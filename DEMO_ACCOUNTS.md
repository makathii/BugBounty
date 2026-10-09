# Demo Accounts (local recording / development only)

All accounts use the password: **Demo1234!**

| Username   | Role        | Notes                                          |
|------------|-------------|------------------------------------------------|
| `parsa`    | Researcher  | Rank #2 on leaderboard, $9,500 earned          |
| `nova`     | Researcher  | Rank #1 on leaderboard                         |
| `raven`    | Researcher  | Has an accepted + a rejected + duplicate report|
| `cipher`   | Researcher  | Has open/triaged reports                       |
| `acme`     | Company     | Acme Corp — 2 programs, 8 reports, $4k paid    |
| `techflow` | Company     | TechFlow GmbH — 1 program, top payouts         |
| `triager`  | Triager     | **Requires 2FA code** (see below)              |
| `admin`    | Admin       | Superuser, **requires 2FA code** (see below)   |

## 2FA for triager / admin

Triager and Admin accounts enforce TOTP two-factor auth (a platform security
feature). Both demo accounts share this secret:

```
VFYKSMK7JXS2HNKEB6S4R3HYD36H5PGO
```

Add it to any authenticator app (Google Authenticator, 1Password, etc.), or
generate the current 6-digit code from the terminal while recording:

```bash
docker exec bugbounty-backend python -c "import pyotp; print(pyotp.TOTP('VFYKSMK7JXS2HNKEB6S4R3HYD36H5PGO').now())"
```

The login form reveals the "2FA Code" field automatically after the first
attempt without a code.

## Email verification (new registrations)

Emails are printed to the backend console. After registering on camera, grab
the verification link with:

```bash
docker logs bugbounty-backend --tail 50 | grep -o 'http://localhost:3000/verify-email/[a-zA-Z0-9]*'
```

## Re-seeding

```bash
docker exec -i bugbounty-backend python manage.py shell < backend/seed_demo.py
docker exec bugbounty-backend python manage.py recompute_leaderboard
```
