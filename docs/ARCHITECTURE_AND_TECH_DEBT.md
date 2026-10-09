# Architecture Decisions, Technical Debt & Optimization Roadmap

> **Scope note.** "InnoLab 2" does not appear anywhere in this repository, so this
> review treats this repo (`makathii/BugBounty`) as that codebase. If InnoLab 2 is a
> different project, point me at it and I'll redo this.
>
> **Method.** Static review of the Django backend (`Backend/`) and React frontend
> (`Frontend/`). Nothing here was profiled against a running database; items are
> marked by confidence. Architecture decisions are *inferred from the code* and
> should be confirmed by the people who made them.

## 1. System overview

| Layer | Stack | Notes |
|---|---|---|
| API | Django 5.2 + DRF 3.16 | Apps: `users`, `reports`, `programs`, `audit`, `leaderboard`, `core` (CVSS) |
| Auth | SimpleJWT in httpOnly cookies, header fallback | MFA (pyotp), OAuth, lockout, sessions table |
| DB | PostgreSQL 15 | One migration (`0001_initial`) per app |
| Frontend | React (CRA / `react-scripts`) | ~9.7k lines JSX, inline styles |
| Infra | docker-compose: db, backend, frontend, clamav | Backend runs `runserver` |
| Size | ~12.4k lines Python (≈45% tests) | |

## 2. Architecture decision records (inferred)

### ADR-1 Cookie-based JWT with header fallback
- **Decision:** `JWTCookieAuthentication` first, `Authorization: Bearer` second (`settings.py` REST_FRAMEWORK comment says "during migration").
- **Why:** httpOnly cookies keep tokens away from XSS; CSRF token + SameSite cover the cookie risk.
- **Consequence:** two auth paths to test and secure. *Debt:* remove the header fallback once tests/integrations migrate.

### ADR-2 Role-based access via Django `Group` names
- **Decision:** roles are groups named `Researcher`, `Triager`, `Admin`, `ProgramOwner`, checked with `user.groups.filter(name=...)`.
- **Consequence:** cheap to start, but the strings are repeated across ~25 call sites and each check is a DB query (see perf doc §3.1). *Debt:* centralize in a `roles.py` helper and cache on the request.

### ADR-3 Program "company" is a `User`, with a separate `Company` profile
- `Program.company` FK → `User`; `Company` is a 1:1 profile. Queries read `program__company=user`.
- **Consequence:** confusing naming (a "company" field that holds a user). Safe to leave, costly to rename late.

### ADR-4 Leaderboard as an append-only-ish ledger (`ScoreEvent`) kept in sync by signals
- **Decision:** `leaderboard/services.py` is the only writer; `post_save` on `BugReport` calls an idempotent `sync_report_score`; `recompute_leaderboard` rebuilds from scratch.
- **Why:** rankings are derived data, reproducible, and rebalanceable via `LEADERBOARD_SEVERITY_POINTS`.
- **Consequence:** good isolation. Ranking is computed per request (§ perf doc 3.4) and there are now **two** severity score tables (`BugReport.severity_score` 1–4 in `reports/signals.py`, ledger points 1/3/7/15 in settings).

### ADR-5 Denormalized stats via snapshots (`ProgramStats`) refreshed from signals
- Every `BugReport` save/delete calls `program.refresh_stats()` synchronously, wrapped in `except Exception: pass`.
- **Consequence:** simple reads, but write amplification and silent failures.

### ADR-6 Defense-in-depth for uploads and web security
ClamAV scan, extension + MIME allowlist (python-magic), EXIF stripping, dimension limits, bleach sanitizers, CSP with nonces, argon2, django-ipware with trusted-proxy count, per-scope throttles, `SecurityAuditLog` middleware. This is the strongest part of the codebase and is well covered by tests.

### ADR-7 Backend baked into image (no bind mount)
Documented in `docker-compose.yml` (VirtioFS `EDEADLK` on macOS). Consequence: every backend change needs `docker compose up --build`.

## 3. Technical debt register

Severity: **H** fix soon · **M** plan it · **L** opportunistic.

### Security / configuration
| # | Sev | Finding | Where |
|---|---|---|---|
| T1 | **H** | Plaintext credentials in comments (superuser/test/researcher passwords). They are in git history, so **rotate them** even after deleting the comment. | `Backend/Backend/settings.py` (end of file), also `DEMO_ACCOUNTS.md` |
| T2 | **H** | Insecure `SECRET_KEY` fallback only *warns* when `DEBUG` is false. Should fail to start. | `settings.py` top |
| T3 | **H** | `DATABASES` is hardcoded (`HOST='db'`, `postgres/postgres`); `DATABASE_URL`/`POSTGRES_*` passed by compose are ignored. No `CONN_MAX_AGE`. | `settings.py` ~L238 |
| T4 | M | Backend container runs `manage.py runserver` (dev server); no gunicorn/uvicorn, no static serving plan. | `docker-compose.yml` |
| T5 | M | Public reCAPTCHA *test* key is the frontend default; works in any environment so a missing env var fails open. | `CompanyRegister.jsx` |

### Backend code
| # | Sev | Finding | Where |
|---|---|---|---|
| T6 | M | `ActivityLog` contains stray copies of report fields (`steps_to_reproduce`, `impact`, `vulnerability_type`, `affected_url`) — looks like a paste error; `__str__` also triggers a query for `report.title`. | `reports/models.py` end |
| T7 | M | `ProgramStats` counts an `info` severity that `BugReport.SEVERITY_CHOICES` does not allow, so `info_count` is always 0. | `programs/models.py`, `reports/models.py` |
| T8 | M | Same program-stats logic implemented twice (`ProgramViewSet` ~L253 and dashboard view ~L588) and again in `ProgramStats.snapshot_for`. | `programs/views.py`, `programs/models.py` |
| T9 | M | `except Exception: pass` around `refresh_stats()` hides real failures. | `reports/signals.py` |
| T10 | M | `find_potential_duplicates`: (a) `Q(affected_url=self.affected_url)` with an empty URL matches *every* report with no URL; (b) comment says "recent 50" but the model has no default ordering, so `[:50]` is arbitrary. This is a correctness bug as well as a perf issue. | `reports/models.py` |
| T11 | L | Large view modules (`users/views.py` 700, `programs/views.py` 704, `reports/views.py` 683 lines) mix permission checks, business logic and email sending. Extract services like `leaderboard/services.py` already does. | |
| T12 | L | Duplicate imports and `Attachment` split into `models_attachment.py`. | `reports/` |
| T13 | L | Role literals (`'Triager'`, `'Admin'`…) repeated ~25×. | ADR-2 |

### Repo / tooling
| # | Sev | Finding |
|---|---|---|
| T14 | M | Tracked junk: `Backend/pytest 2.ini` (copy of `pytest.ini`), `Backend/test_db.sqlite3-journal`, `Backend/docker-compose.yml` (duplicate of root compose). Add to `.gitignore`/delete. |
| T15 | M | Duplicate/overlapping tests: `reports/test_file_upload_security.py` vs `tests/test_file_upload_security.py`, plus `reports/tests.py`, `users/tests.py`, `tests/test_reports.py`. `run_tests.sh` special-cases one of them. |
| T16 | M | No CI. Tests only run through `run_tests.sh` inside Docker. Merge-conflict markers reached `dev` (fixed in `8cfeb6e`) — a CI build would have caught it. |
| T17 | M | `Frontend/package-lock.json` out of sync with `package.json` (`npm ci` fails: missing `yaml@2.9.1`); `npm run build` fails on `jest/globals` ESLint config unless `DISABLE_ESLINT_PLUGIN=true`. |

### Frontend
| # | Sev | Finding |
|---|---|---|
| T18 | M | `ProgramBrowser.jsx` still uses simulated `setTimeout` data instead of `/programs/researcher/`. |
| T19 | L | Very large components (`ProgramWizard` 781, `ProgramBrowser` 771, `ReportDetail` 687 lines), all-inline styles duplicated across files; `badge()` helper puts a non-style `text` key in the style object. |
| T20 | L | Create-React-App is deprecated; plan a move to Vite. |

## 4. Optimization roadmap

**Phase 0 – Hygiene (≈1–2 days).** T1 rotate + scrub, T2 fail-fast secret, T3 env-driven `DATABASES` (+`CONN_MAX_AGE=60`), T14 delete junk, T17 fix lockfile/ESLint, T16 add CI (lint + `pytest` + `npm run build`).

**Phase 1 – Correctness (≈2–3 days).** T10 duplicate-detection fix, T6/T7 model clean-up (migration), T9 log instead of swallow, T15 de-duplicate tests.

**Phase 2 – Performance quick wins (≈3–5 days).** See `QUERY_PERFORMANCE.md` §5 phases A–B (indexes, `select_related`, annotate counts, single-aggregate dashboards, role-check caching).

**Phase 3 – Structure (≈1–2 weeks).** T11/T13 extract `roles.py` + service modules, T8 one stats implementation, T4 gunicorn + production compose profile, remove header-JWT fallback (ADR-1).

**Phase 4 – Scale (as needed).** Move `refresh_stats` and email to a task queue, cache leaderboard, partition/retain `SecurityAuditLog`, Vite migration (T20), finish real API wiring (T18).

### Suggested success metrics
- p95 latency of `/api/reports/`, `/api/leaderboard/`, `/api/programs/` under a 100k-report seed.
- Queries per request (asserted with `assertNumQueries` for list endpoints).
- CI green on every PR; zero secrets in `git grep`.
