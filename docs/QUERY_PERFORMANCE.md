# Query Performance Analysis, Indexing Strategy & Roadmap

> **Important:** this is a *static* analysis of ORM code and model definitions.
> No queries were executed and no `EXPLAIN` plans were captured, because no seeded
> database was available. Treat estimates as hypotheses and use §6 to confirm each
> one before shipping a migration.

## 1. Current index inventory

| Table | Existing indexes |
|---|---|
| `reports_bugreport` | **None declared** apart from the automatic FK indexes (`reporter`, `program`, `assigned_to`, `duplicate_of`) and PK |
| `reports_comment`, `reports_activitylog` | FK index on `report` only |
| `reports_attachment` | `(report, scan_status)` |
| `programs_program` | `(status, scope_type)`, `(company, status)`, `(slug)` + `slug UNIQUE` |
| `programs_programstats` | `UNIQUE(program, date)` + `(program, date)` |
| `programs_programinvitation/application` | `UNIQUE(program, researcher)`, `(program, status)`, `(researcher, status)` |
| `leaderboard_scoreevent` | `awarded_at`, `(researcher, awarded_at)`, `(program, awarded_at)` |
| `audit_securityauditlog` | `timestamp`, `(action,-ts)`, `(user,-ts)`, `(ip_address,-ts)`, `(severity,-ts)` |

`BugReport` is the hottest and largest table and has the weakest indexing.

## 2. Hot paths reviewed

Report list/detail/triage dashboard (`reports/views.py`), program list/stats/dashboards (`programs/views.py`, `programs/serializers.py`), leaderboard (`leaderboard/services.py`), post-save signals, duplicate detection, audit middleware.

## 3. Query-level bottlenecks (ranked)

**3.1 Role checks hit the DB repeatedly — *High confidence*.**
`user.groups.filter(name__in=[...]).exists()` is a join query each time. `BugReportViewSet.get_queryset` runs two (`reports/views.py:66-67`), and individual actions plus permission classes add more (`:124, 210, 297, 406, 427, 463, 495, 522, 643, 680`). A single report detail request can run 3–5 identical group queries.
*Fix:* a `get_roles(user)` helper that loads group names once and memoizes on `request`/`user` (`user._roles`).

**3.2 N+1 queries in list endpoints — *High confidence*.**
- `BugReportSerializer.get_assigned_to_username` / `get_program_name` read FKs, but `get_queryset` has no `select_related('assigned_to','program')` (`reports/views.py:40`). → +2 queries per row.
- `ProgramListSerializer.get_favorites_count` and `ProgramDetailSerializer.get_in_scope_count / out_of_scope_count` run `.count()` per program (`programs/serializers.py:84-129`). → up to +3 per row.
*Fix:* `select_related`, and `annotate(favorites_count=Count('favorites', distinct=True), in_scope=Count('scopes', filter=Q(scopes__is_in_scope=True), distinct=True))`.

**3.3 Counting with many round-trips — *High confidence*.**
`triage_dashboard` runs 7 separate `COUNT(*)` on `BugReport` (`reports/views.py:131-138`). `ProgramStats.snapshot_for` runs ~9 queries, and `programs/views.py` repeats the pattern.
*Fix:* one `aggregate()` using `Count('id', filter=Q(status='open'))` etc. → 1 query per dashboard.

**3.4 Leaderboard recomputed and ranked in Python on every request — *✅ done (phase D)*.**
`leaderboard_rows` used to materialize every researcher into a Python list; the page was a slice of it, and `rank_for` re-ran the full aggregation and looped.
*Done:*
- **Rank in SQL:** `services._ranked_queryset` aggregates per researcher and assigns `ROW_NUMBER()` as a window function, ordered by points, report count, latest award and finally researcher id (the old ordering left full ties undefined). `leaderboard_page(limit, offset)` pages with `LIMIT/OFFSET` in the database and returns `(rows, total)`; the list endpoint uses it. `leaderboard_rows` remains as a thin wrapper.
- **`rank_for`:** rank = 1 + number of researchers ordered strictly before this one (a `HAVING` count), two small queries, nothing materialized. (A first attempt filtered the window query by researcher, which applies the filter *before* the window and returned rank 1; a test caught it.)
- **Cache:** pages and ranks are cached for `LEADERBOARD_CACHE_TTL` seconds (default 30, 0 disables). Keys include a version number bumped on every `ScoreEvent` save/delete (including the cascade when a report is deleted) and by `recompute_all`.
- **`recompute_all`:** single transaction, one bulk insert, so readers never see an empty ledger and a failure rolls back (3.11 ✅).
*Caveat:* the project has no `CACHES` setting, so Django's default per-process `LocMemCache` is used. With several workers, an invalidation is visible only to the process that made it; others serve stale pages for up to the TTL. Configure Redis/Memcached for immediate, global invalidation.
*Not done:* a `ResearcherScore` rollup table. The all-time aggregation still scans the whole ledger on a cache miss; add the rollup only if misses become slow at real data volumes.

**3.5 Signal write amplification on every report save — *High confidence; ✅ done (phase C)*.**
`reports/signals.on_report_saved` computed derived fields post-save and re-`save()`d the instance, which re-fired every `post_save` receiver (program stats and the leaderboard ledger ran twice); stats and ledger work also ran on edits that couldn't affect them. *Measured on SQLite with `CaptureQueriesContext` (earlier drafts of this doc over-estimated this at ~15):* create 8 queries, status change to triaged 8, unrelated field edit 4.
*Done:* derived fields (`severity_score`, `time_to_*`) are now set in `BugReport.save()` before the write; `BugReport` remembers loaded values so `save()` flags whether stats (`_stats_programs`, including the *old* program when a report moves) or the ledger (`_score_dirty`) need work; `Program.refresh_stats_for(id)` is one aggregate + one `UPDATE` with no model fetch; the blanket `except Exception: pass` is gone.
*Result (same measurement):* create 4, status change 4, unrelated edit **1**, accept 5 (UPDATE + 2 stats + ledger lookup/insert).
*Not done:* deferring `refresh_stats` to `transaction.on_commit` / a task queue. pytest-django's transaction-wrapped tests never run on-commit callbacks, so the existing suite would need `django_capture_on_commit_callbacks` first; revisit with phase E. Note `ProgramStats.snapshot_for` (≈9 queries) is *not* called from the signal path — only the cheap `refresh_stats` is.

**3.6 `icontains` search on `title` and `description` — *High confidence*.**
`Q(title__icontains)|Q(description__icontains)` (`reports/views.py:60-63`) is a sequential scan on a `TextField`. B-tree indexes cannot help.
*Fix:* `pg_trgm` GIN indexes (`TrigramExtension` + `GinIndex(OpClass(Upper('title'), 'gin_trgm_ops'))`) or a `SearchVector` column with GIN if relevance ranking is wanted.

**3.7 Duplicate detection — *High confidence*.**
`WHERE (program_id = X OR affected_url = Y) AND id != … AND status != 'duplicate' AND duplicate_of_id IS NULL` with no ordering, then up to 50 `SequenceMatcher` comparisons in Python. `affected_url` is unindexed (URLField, varchar 200) so the OR can't use a bitmap-OR and degrades to a scan; with `affected_url=''` it matches every URL-less report (correctness bug, see tech-debt T10).
*Fix:* skip the URL clause when empty; `order_by('-created_at')`; index `(program, -created_at)` and `affected_url`; narrow with `.only('id','title','description','affected_url')`; optionally pre-filter candidates with `pg_trgm` `%` on title.

**3.8 Role-scoped visibility queries — *Medium*.**
`ProgramViewSet.get_queryset` (researcher branch) and `ResearcherProgramList` OR three querysets then `.distinct()` (`programs/views.py:57-80, 522-533`). `DISTINCT` over a join forces sort/hash. Replace with `Q(...) | Q(pk__in=Subquery)` / `Exists()` so no duplicates are produced and `distinct()` can go.

**3.9 Audit log write path — *Medium; retention ✅ done (phase E), index pruning pending data*.**
Middleware inserts a row synchronously per 403/admin hit; the table carries 5 indexes (write-amplified) and had no retention.
*Done:* `manage.py purge_audit_logs` (`--days`, `--batch-size`, `--dry-run`; default `AUDIT_LOG_RETENTION_DAYS`=365, 0 = keep forever) deletes in small batches so it never holds long locks. Schedule it daily from cron/your scheduler.
*Not done:* dropping the `severity` / `ip_address` composite indexes. Decide from `pg_stat_user_indexes.idx_scan` on real traffic; removing them blind could slow the admin audit views.

**3.10 Unbounded list endpoints — *Medium*.**
`REST_FRAMEWORK` has no `DEFAULT_PAGINATION_CLASS`; list views that don't set one return full tables (e.g. `Comment` list, `triage` filters). Set a global `LimitOffsetPagination`/`PageNumberPagination` default (`PAGE_SIZE=25`, max 100).

**3.11 `recompute_all` — *Low (batch job)*.**
Deletes the whole ledger then calls `sync_report_score` per report (1 select + 1 write each, N+1). Wrap in `transaction.atomic()` and `bulk_create` from a single annotated queryset.

## 4. Indexing strategy

Rule: add an index only for a query that exists above; verify with `EXPLAIN` (§6); remove what `pg_stat_user_indexes` shows unused.

### 4.1 Add
```python
# reports/models.py  BugReport.Meta
indexes = [
    models.Index(fields=["status", "-created_at"],            name="rpt_status_created"),   # triage lists, dashboard
    models.Index(fields=["program", "status"],                name="rpt_program_status"),  # program stats, owner view
    models.Index(fields=["program", "-created_at"],           name="rpt_program_created"), # duplicates, recent
    models.Index(fields=["reporter", "-created_at"],          name="rpt_reporter_created"),# "my reports"
    models.Index(fields=["assigned_to", "status"],            name="rpt_assignee_status"), # "assigned to me"
    models.Index(fields=["-created_at"],                      name="rpt_created"),         # default ordering
    models.Index(fields=["affected_url"],                     name="rpt_url"),             # duplicate lookup
]
# partial index for the common "unassigned" filter
models.Index(fields=["created_at"], condition=Q(assigned_to__isnull=True), name="rpt_unassigned")
```
```python
# Trigram search (requires: CREATE EXTENSION pg_trgm via TrigramExtension migration)
GinIndex(OpClass(Upper("title"), name="gin_trgm_ops"), name="rpt_title_trgm")
GinIndex(OpClass(Upper("description"), name="gin_trgm_ops"), name="rpt_desc_trgm")
```
Other tables:
- `Comment`: `Index(fields=["report", "created_at"])`
- `ActivityLog`: `Index(fields=["report", "-created_at"])`
- `ScoreEvent`: keep as is; add `Index(fields=["awarded_at", "researcher"])` only if the window-function query plan shows a sort on the all-period path.

### 4.2 Remove (redundant)
- `Program`: `Index(fields=['slug'])` — `slug` is already `unique=True` (`programs/models.py:106`).
- `ProgramStats`: `Index(fields=['program','date'])` — duplicates `unique_together` (`:369`).
- `ProgramFavorite`/others: confirm after measuring; unique constraints already provide the leading `(program, researcher)` index.

### 4.3 Trade-offs
`BugReport` is write-light compared with read, so ~7 B-tree indexes are acceptable, but the signal churn in §3.5 multiplies index maintenance; fix that first or the new indexes make saves slower. Create indexes on the live table with `AddIndexConcurrently` (`django.contrib.postgres.operations`, `atomic = False`).

## 5. Optimization roadmap

| Phase | Work | Expected gain | Risk |
|---|---|---|---|
| **A – No-schema quick wins** (1–2 d) | 3.1 role cache; 3.2 `select_related` + annotated counts; 3.3 single-aggregate dashboards; 3.10 default pagination; 3.7 empty-URL fix + ordering | Query count per list request drops from O(rows) to O(1); dashboard 7→1 queries | Low |
| **B – Indexes** (1 d + review) | §4.1 `BugReport` indexes (concurrently), §4.2 removals, trigram search | Filter/sort/search move from seq scan to index scan | Low–Med (index build time/lock if not concurrent) |
| **C – Write path** (2–3 d) | 3.5 ✅ derived fields in `save()` + conditional stats/ledger; ⏳ `on_commit`/queue, 3.11 atomic bulk recompute | Report save 8 → 4 queries (1 for unrelated edits); fewer index writes | Med (behavior of signals tested in `test_leaderboard`, `test_reports_workflow`) |
| **D – Leaderboard** (2 d) ✅ | 3.4 SQL window ranking + 30 s cache, atomic bulk recompute | Page cost independent of researcher count; cache hit = 0 queries | Med (tie-break parity with current ordering) |
| **E – Scale** (as needed) | ✅ `CONN_MAX_AGE` + env-driven DB config, shared Redis cache, audit-log retention; ⏳ task queue (Celery) for stats/email, PgBouncer, read replica, audit partitioning | Headroom beyond ~1M reports | Higher (ops) |

## 6. How to validate (do this before and after each phase)

1. **Seed realistic data:** extend `seed_demo.py` (or a `seed_perf` command) to ~100k reports, ~5k users, ~200 programs, 200k comments, 100k score events.
2. **Count queries:** `django-debug-toolbar` locally, and `assertNumQueries` / `django_assert_max_num_queries` tests for: report list (page of 25), program list, triage dashboard, leaderboard, report save.
3. **Plans:** for each query in §3 run `EXPLAIN (ANALYZE, BUFFERS)` via `qs.explain(analyze=True, buffers=True)`; record Seq Scan → Index Scan and buffer hits.
4. **Production signal:** enable `pg_stat_statements`, `log_min_duration_statement=200ms`; review `pg_stat_user_indexes` (unused) and `pg_stat_user_tables` (seq_scan counts) after a week.
5. **Load:** k6/Locust against `/api/reports/?status=open`, `/api/leaderboard/`, `POST /api/reports/`; compare p50/p95 before/after.

## 7. Prioritized checklist
- [x] A: role cache (`core/roles.py`, reports + program views), `select_related`, annotated favorites count, aggregate triage dashboard
- [ ] A: pagination default (deferred: changes list response shape, needs frontend coordination)
- [x] A: fix empty-`affected_url` duplicate match + newest-first ordering
- [x] B: `BugReport` composite indexes (migration `reports/0002`; plain `CREATE INDEX`, see note)
- [ ] B: trigram search; build indexes `CONCURRENTLY` on a large live table
- [x] B: drop redundant `slug` / `(program,date)` indexes (migration `programs/0002`)
- [x] C: remove post-save re-save; conditional stats/ledger work (1–4 queries per save instead of 4–8)
- [ ] C: `on_commit`/queued `refresh_stats` (see 3.5)
- [x] D: window-function leaderboard + cache (see 3.4 caveat on LocMemCache)
- [x] E: audit-log retention command, env-driven DB config + persistent connections, optional shared Redis cache
- [ ] E: task queue for stats/email, read replica, audit index pruning (need production data / an infra decision)
