# Browser end-to-end tests

Real Chromium against a real backend (PostgreSQL, real middleware and auth) with the demo data.
They cover the flows that matter most and that unit tests can't. `journeys/` starts from nothing (sign
up, verify the emailed link, log in, 2FA, password reset, reports, triage, companies, private
programs) and ends with a sweep of every page at laptop and phone size; the specs next to it cover
comments, points/levels/badges and the store. See `docs/FULL_PROGRAM_TEST.md` for what each journey
proves and what the suite found.

In CI (`.github/workflows/ci.yml`, job **e2e**) everything is started for you. To run them locally:

```bash
# 1. a throwaway PostgreSQL database with demo data (the tests RESET demo state: comments,
#    purchases, wallet rows; never point them at data you care about)
export POSTGRES_HOST=localhost POSTGRES_USER=postgres POSTGRES_PASSWORD=postgres POSTGRES_DB=bb_e2e
export DJANGO_SETTINGS_MODULE=config.e2e_settings DJANGO_SECRET_KEY=any-string-of-20-or-more-chars
cd backend
python manage.py migrate
python manage.py shell < scripts/seed_demo.py
python manage.py runserver 8000 --noreload &

# 2. the frontend, built against that API and served on :3000 (client-side routes need a SPA server)
cd ../frontend
REACT_APP_API_URL=http://localhost:8000/api npm run build
npx serve -s build -l 3000 &

# 3. run (first time: npx playwright install chromium)
npm run e2e
```

Emails are written to files (`E2E_MAIL_DIR`, default `/tmp/bugbounty-e2e-mail`) so the tests can follow
verification and reset links; `e2e_settings` also turns off database connection reuse, otherwise the dev
server's thread-per-request connections exhaust PostgreSQL during a long run.

Useful variables: `E2E_PYTHON` (python that has the backend requirements, if not `python`),
`PLAYWRIGHT_CHROMIUM_PATH` (use an already installed Chromium), `E2E_BASE_URL`, `E2E_API_URL`.

How it works: `global-setup.js` runs `backend/scripts/e2e_prepare.py` (refuses to run unless
`E2E_RESET=1`), which resets the demo state and mints login tokens into `e2e/.state.json`;
specs log in by putting those tokens in localStorage, and cross-check what the page shows
against the API instead of hard-coding numbers. The specs run in order and share one database.
