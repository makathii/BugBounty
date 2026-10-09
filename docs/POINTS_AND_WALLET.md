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

## Levels

A researcher's level is a pure function of **lifetime earned** points, so it is never stored and
spending never changes it (revoked points can). The ladder lives in `leaderboard/levels.py`
(override with `settings.LEADERBOARD_LEVELS`, a list of `(min_points, title)` starting at 0):

| Level | Title         | Lifetime points |
|-------|---------------|-----------------|
| 1     | Bug Sprout    | 0               |
| 2     | Bug Hatchling | 50              |
| 3     | Bug Scout     | 150             |
| 4     | Bug Hunter    | 350             |
| 5     | Bug Wrangler  | 700             |
| 6     | Bug Slayer    | 1,200           |
| 7     | Bug Whisperer | 2,000           |
| 8     | Bug Legend    | 3,500           |

- `GET /api/levels/` the ladder; `GET /api/levels/me/` your level, progress and points to next
- `/api/wallet/` and every leaderboard row include the level (leaderboard rows show the
  *lifetime* level even when ranking a 7-day window)
- The UI shows a progress card on the dashboard and wallet, a chip on the leaderboard, and a
  one-time "Level up!" banner (remembered per browser in localStorage)

## Badges

Badges are achievements, defined in code (`badges/definitions.py`) and awarded automatically
whenever a researcher's points ledger changes. Only *who earned what, when* is stored
(`badges.UserBadge`). Once earned a badge is kept, even if the report behind it is later rejected.

| Badge | Rule |
|-------|------|
| 🩸 First Blood | first report accepted |
| 💥 Critical Thinker | a critical report accepted |
| 🔨 Heavy Hitter | 3 high or critical reports accepted |
| 🐞 Bug Collector | 10 reports accepted |
| 🏆 Bug Hoarder | 25 reports accepted |
| 🌍 Globetrotter | accepted reports in 3 different programs |
| ⭐ Standout Report | a triager gave bonus points |
| ✨ Clean Streak | 5 accepted in a row without a rejection (duplicates and open reports are neutral) |

To add a badge, add one `Badge(...)` line (a key, name, description, icon and a
`progress(stats) -> (current, target)` rule); no migration is needed. Run
`python manage.py award_badges` to hand out new badges to people who already qualify
(`GET /api/badges/` also catches the caller up). The dashboard shows a shelf with a one-time
"New badge" banner and `/badges` shows every badge with progress on the locked ones.

## The store

Items are cosmetics for a researcher's character, bought with wallet points.

- **Item**: name, `slot` (hat / face / body / pet / background), `rarity`, `price` (0 = free
  starter item), `min_level`, `art` (an emoji placeholder until real artwork exists; `image_url`
  overrides it), `is_active` (retire an item without deleting it; owners keep it).
- **Inventory** (`UserItem`): one row per user per item, with the price actually paid and the
  wallet transaction behind it.
- **Loadout** (`EquippedItem`): at most one owned item per slot.
- Buying (`store.services.purchase`) is one database transaction: the user row is locked, then
  it checks retired / already owned / level (from *lifetime* points, so spending never locks you
  out) / balance, charges the wallet and adds the item together or not at all.
- Refunds go through `store.services.refund` (admin action on the inventory): the points go back
  and the item is taken off.

**In the app:** `/store` has a Shop tab and a My items tab, slot filters, a live character preview
with a "Try on" button on every item (so you can see an item before paying), and buy / wear / take
off buttons that explain themselves (needs level N, X pts short, ...). Your character appears on
the dashboard and next to every name on the leaderboard. The character is drawn by
`components/character/Character.jsx` from each item's `art` emoji or `image_url`, so swapping in
real artwork later only means filling in `image_url` on the items; leaderboard rows include each
researcher's `loadout` for this. Report comments show the author's character too
(`author_loadout` on each comment; deleted comments show none).

Set up the starter catalogue with `python manage.py seed_store` (idempotent; it never overwrites
prices you changed). Edit items, prices and levels in the Django admin.

API (all need login): `GET /api/store/items/` (`?slot=`, `?rarity=`; each item says
`owned` / `equipped` / `locked` / `can_afford`), `POST /api/store/items/{slug}/purchase/`,
`.../equip/`, `.../unequip/`, `GET /api/store/inventory/`, `GET /api/store/loadout/` and
`GET /api/store/loadout/{user_id}/`. Purchase errors carry a `code`: `insufficient_points` (400),
`level_too_low` (403), `already_owned` (409), `item_unavailable` (404).

Note: if an accepted report is revoked *after* its points were spent, the balance can go negative.
That is intentional (it is honest bookkeeping); purchases are simply blocked until it recovers.

## API

- `GET /api/wallet/`: balance, lifetime earned, total spent, ten most recent transactions
- `GET /api/wallet/transactions/?limit=&offset=`: paged history
- `GET /api/levels/`, `GET /api/levels/me/`, `GET /api/badges/`
- `POST /api/reports/{id}/accept/` accepts `bonus_points`; reports expose `bonus_points` and `points_awarded`
