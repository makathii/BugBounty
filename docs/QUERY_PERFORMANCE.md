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

**3.4 Leaderboard recomputed and ranked in Python on every request — *High confidence on shape, medium on cost*.**
`leaderboard_rows` aggregates all `ScoreEvent` rows in the window, materializes *every* researcher into a Python list, and `list()` then slices a page. `rank_for` (used by `/me/` and `/<id>/`) re-runs the full aggregation and loops linearly.
- Cost grows with total researchers × events; "all" period can never use the date index.
*Fix (in order):* (1) push ranking into SQL with `Window(RowNumber/Rank)` and paginate in the DB, `rank_for` filters one row; (2) cache per `(period, program)` for 30–60 s, invalidated by `sync_report_score`; (3) if still hot, maintain a `ResearcherScore` rollup table.

**3.5 Signal write amplification on every report save — *High confidence*.**
One `BugReport.save()` triggers: `reports/signals.on_report_saved` → possible second `save()` (re-fires all post_save receivers) → `program.refresh_stats()` (~9 queries + upsert) → `leaderboard.on_report_saved` → `ScoreEvent` select + maybe insert/update. Roughly 15+ queries per save, run synchronously in the request.
*Fix:* compute `severity_score` / timing fields in `save()` (or `pre_save`) instead of a post-save re-save; run `refresh_stats` via `transaction.on_commit` and debounce/queue it; only refresh when `status`, `severity`, `bounty_amount` or `program` changed.

**3.6 `icontains` search on `title` and `description` — *High confidence*.**
`Q(title__icontains)|Q(description__icontains)` (`reports/views.py:60-63`) is a sequential scan on a `TextField`. B-tree indexes cannot help.
*Fix:* `pg_trgm` GIN indexes (`TrigramExtension` + `GinIndex(OpClass(Upper('title'), 'gin_trgm_ops'))`) or a `SearchVector` column with GIN if relevance ranking is wanted.

**3.7 Duplicate detection — *High confidence*.**
`WHERE (program_id = X OR affected_url = Y) AND id != … AND status != 'duplicate' AND duplicate_of_id IS NULL` with no ordering, then up to 50 `SequenceMatcher` comparisons in Python. `affected_url` is unindexed (URLField, varchar 200) so the OR can't use a bitmap-OR and degrades to a scan; with `affected_url=''` it matches every URL-less report (correctness bug, see tech-debt T10).
*Fix:* skip the URL clause when empty; `order_by('-created_at')`; index `(program, -created_at)` and `affected_url`; narrow with `.only('id','title','description','affected_url')`; optionally pre-filter candidates with `pg_trgm` `%` on title.

**3.8 Role-scoped visibility queries — *Medium*.**
`ProgramViewSet.get_queryset` (researcher branch) and `ResearcherProgramList` OR three querysets then `.distinct()` (`programs/views.py:57-80, 522-533`). `DISTINCT` over a join forces sort/hash. Replace with `Q(...) | Q(pk__in=Subquery)` / `Exists()` so no duplicates are produced and `distinct()` can go.

**3.9 Audit log write path — *Medium*.**
Middleware inserts a row synchronously per 403/admin hit; the table carries 5 indexes (write-amplified) and has no retention. *Fix:* keep `timestamp`, `(user,-ts)`, `(action,-ts)`; drop `severity` and `ip` composites unless a query needs them (check `pg_stat_user_indexes.idx_scan`); add retention (monthly partitions or a purge job).

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
| **C – Write path** (2–3 d) | 3.5 move derived fields to `save()`, `on_commit` + conditional stats refresh, 3.11 atomic bulk recompute | Report save ~15 → ~4 queries; fewer index writes | Med (behavior of signals tested in `test_leaderboard`, `test_reports_workflow`) |
| **D – Leaderboard** (2 d) | 3.4 SQL window ranking + 30–60 s cache | Constant-time page + rank | Med (tie-break parity with current ordering) |
| **E – Scale** (as needed) | Task queue for stats/email, audit-log retention/partitioning (3.9), `CONN_MAX_AGE` + PgBouncer, read replica | Headroom beyond ~1M reports | Higher (ops) |

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
- [ ] C: remove post-save re-save; `on_commit` conditional `refresh_stats`
- [ ] D: window-function leaderboard + cache
- [ ] E: audit-log retention, connection pooling
