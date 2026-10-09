# Points and the wallet

Points replace money on this platform. Researchers earn them for accepted reports and (soon) spend
them in a store on cosmetic extras.

## Earning

A report earns points once it is **accepted** or **resolved** (and is not a duplicate):

| Severity | Points |
|----------|--------|
| low      | 10     |
| medium   | 30     |
| high     | 70     |
| critical | 150    |

On accepting a report a triager can add **bonus points** (0–1000, e.g. for an especially clear
write-up). Researchers cannot set them. The table lives in `settings.LEADERBOARD_SEVERITY_POINTS`;
change it and run `python manage.py recompute_leaderboard`.

The award for a report is kept in the `leaderboard.ScoreEvent` ledger (one row per report). If a
report later stops qualifying (rejected, marked duplicate), its points are revoked automatically.

## Two numbers per researcher

- **Lifetime earned**: the sum of the ScoreEvent rows. The leaderboard ranks by this and it never
  goes down by spending.
- **Balance**: lifetime earned + the sum of `wallet.WalletTransaction` rows (purchases are
  negative; refunds and staff adjustments can be either). This is what the store will spend.

`WalletTransaction` is append-only. To undo a purchase use `wallet.services.refund()`; staff can
grant or claw back points from the Django admin (it records who and why).

## For the store (next step)

`wallet.services.spend(user, amount, reason, reference="item:<id>")` is the only way to spend. It
locks the user's row so two simultaneous purchases cannot overdraw, and raises `InsufficientPoints`
when the balance is too low. The store should call it inside the same transaction that grants the
item.

Note: if an accepted report is revoked *after* its points were spent, the balance can go negative.
That is intentional (it is honest bookkeeping); purchases are simply blocked until it recovers.

## API

- `GET /api/wallet/`: balance, lifetime earned, total spent, ten most recent transactions
- `GET /api/wallet/transactions/?limit=&offset=`: paged history
- `POST /api/reports/{id}/accept/` accepts `bonus_points`; reports expose `bonus_points` and `points_awarded`
