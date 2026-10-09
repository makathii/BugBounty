# BugBounty

Bug bounty platform: companies publish programs, researchers submit reports, triagers review them.
Django REST backend, React frontend, PostgreSQL, Redis, Celery.

## Layout

```
backend/    Django project (config/ + one app per domain: users, reports, programs, audit, leaderboard; core/ helpers)
frontend/   React app (src/features/<feature>/, shared src/components, src/services/api.js, src/styles/theme.css)
docs/       architecture review and performance roadmap (ARCHITECTURE_AND_TECH_DEBT.md, QUERY_PERFORMANCE.md), points and wallet (POINTS_AND_WALLET.md)
```

Backend apps keep `models/` and `views/` as packages with one module per model / resource;
tests mirror the apps under `backend/tests/<app>/`. See `docs/ARCHITECTURE_AND_TECH_DEBT.md`
for the full tree and the reasoning behind it.

## Run

```bash
cp .env.example .env            # set DJANGO_SECRET_KEY at minimum
docker compose up --build       # db, redis, backend, celery worker + beat, frontend, clamav
```

`docker compose up` reuses images it already built. After pulling changes that touch
`backend/` or `frontend/` (new files, new dependencies, renamed folders) run
`docker compose up --build` so the images are rebuilt; a stale backend image fails with
`ModuleNotFoundError: No module named 'config'`.

Frontend: http://localhost:3000, API: http://localhost:8000/api, email inbox (Mailpit): http://localhost:8025
(verification and password-reset emails are delivered there, not to real addresses). Demo data and accounts: `DEMO_ACCOUNTS.md`.

## Test

```bash
./run_tests.sh                  # backend tests inside the container
# or locally (SQLite, no Docker):
cd backend && DJANGO_SETTINGS_MODULE=config.test_settings pytest
cd frontend && npm ci && npm run build
```

## Conventions

- Backend settings module is `config.settings` (`config.test_settings` for tests).
- New frontend screens go in `frontend/src/features/<feature>/`; use the `ui-*` classes from
  `styles/theme.css` instead of inline styles.
- Global stylesheets (Home, auth, register, Wizard, App) overlap on a few selectors, so their load
  order in `App.jsx` matters; see the note there.
