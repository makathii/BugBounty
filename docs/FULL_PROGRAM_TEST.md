# Full-program test

A test of the whole product as people actually use it: a real browser against the real backend
(PostgreSQL), every role, starting from nothing (sign up, verify email, log in, ...) rather than from
pre-made accounts. Run it with `cd frontend && npm run e2e` (setup in `frontend/e2e/README.md`); CI runs
it on every push.

## What it covers (50 browser tests)

| Journey | File | What it proves |
|---|---|---|
| Researcher sign-up | `journeys/researcher-signup` | register, popup, no login before verifying, emailed link, login, empty dashboard; form errors; duplicate username/email; garbage links; wrong password = same message as unknown user |
| 2FA for staff | `journeys/two-factor` | forced enrolment, wrong/right code, backup codes (single use), no replay of a used code, staff cannot disable |
| 2FA for researchers | `journeys/two-factor-optional` | enable, code at login, regenerate backup codes, disable; wrong code cannot disable |
| Password reset | `journeys/password-reset` | emailed link, validation, single-use link, no email enumeration, bogus link |
| Access control | `journeys/access-control` | logged-out redirects, role guards, others' reports unreachable, logout ends the session server-side, password reset signs out other sessions, admin cards |
| Reporting | `journeys/report-submission` | program page -> report filed under that program, program picker, unavailable program, duplicate warning + "submit anyway", no leaks |
| Triage and points | `journeys/triage` | open -> triaged (severity) -> accepted with bonus -> wallet, level, badge, email; rejection with reason; researchers cannot triage |
| Company | `journeys/company` | sign-up, mandatory profile, program wizard, draft hidden, activation, report arrives, company comments, isolation from other companies |
| Private programs | `journeys/private-program` | apply, company approves/rejects, access follows, targets hidden until access |
| Sweep | `journeys/sweep` | every page, every role, laptop and phone: script errors, failed API calls, "undefined"/"NaN", horizontal overflow |
| Earlier suites | `comments`, `points`, `store` | threaded comments, wallet/levels/badges, store |

Behind it: ~810 backend tests (SQLite and PostgreSQL) and ~110 component tests.

## What it found (all fixed, each with regression tests)

Serious:
1. **Logout never reached the server.** The frontend cleared the stored token before sending the request, so the server saw an unauthenticated call (401) and revoked nothing.
2. **"Sign out everywhere" did nothing.** Revoking a session only flipped a flag in the session list; the old access token kept working and the old refresh token kept minting new ones. Sessions now carry an id in both tokens, checked on every request and every refresh. A **password reset now signs out everyone**, so an attacker already logged in is cut off.
3. **Reports were saved with no program.** The program page linked to `/submit?program=<id>` but the page ignored it, so every UI-submitted report belonged to nobody and no company could see it.
4. **No report could ever be accepted.** Nothing could move an open report to "triaged", and only triaged reports can be accepted. Severity (which sets the base points) could not be set anywhere, and researchers were never told about decisions. Added a "Start Triage" step, severity choice, and decision emails.
5. **A one-time 2FA code could be replayed** for about 90 seconds. Codes are now single-use (RFC 6238), recorded atomically.
6. **Duplicate detection leaked other researchers' report titles, ids and usernames.** Others' reports are now anonymised.

Functional:
7. Companies could see reports in their list but got 403 opening them (could not read or discuss reports sent to them).
8. Private programs that take applications, or that you were invited to, were invisible (404), so nobody could apply or accept. Companies also had no screen to review applications (added). Targets/guidelines of private programs are hidden until access is granted.
9. The API accepted reports for draft/closed/ended or private-without-access programs, with no program at all, and let a report be moved between programs.
10. Registration accepted an email already in use (and no email at all); profile update could take someone else's email.
11. A wrong password showed no error (the 401 handler reloaded the login page).
12. The email-verification page reported success for any server error.
13. Server errors about the program or permissions, and the duplicate warning, were never displayed by the report form.

Polish: leaderboard page public while its API needs login; researcher dashboard overflowed phone screens (two-column layouts did not collapse); admin dashboard buttons led to pages that do not exist; a placeholder `alert()` on the company report page.

## Known gaps (not bugs in what exists, but missing or untested)

- ~~Companies cannot invite researchers~~ — fixed: companies invite by username from **My programs → Invitations** (the researcher is emailed, and accepts or declines on their dashboard or the program page).
- The report form has **no file attachments** (the API supports them; antivirus scanning is not exercised by the tests).
- Changing your email in the profile does not re-verify it.
- Not exercised: OAuth sign-in (GitHub/Google/GitLab), reCAPTCHA (off in tests), request rate limits (turned off for the browser run), the Django admin site itself, in-app program notifications.
- Throttling and lockout are covered by backend tests only.
- `resend-verification` looks users up with `.get(email=...)`; accounts that already share an email (from before uniqueness was enforced) would error. Run `python manage.py find_duplicate_emails` on an existing database and resolve any before deploying.
