# Kids Points App — Testing Plan

## Context
The app is built and verified end-to-end manually via `curl`. We now need an
automated test suite so future changes don't quietly break the behaviors that
matter: balance math, overdraft prevention, stock decrement on approval,
PIN-based auth, the last-parent guard, and the kid-vs-parent access split.

The goal is a fast, deterministic suite that gives us confidence to refactor
and add features. It is not a goal to test the framework itself or to chase
high line coverage on glue code.

## Goals
- Cover every rule from PLAN.md "Key Behaviors & Edge Cases" with at least
  one test that fails if the rule is broken.
- Cover the access split: kids can't reach parent views, parents can't reach
  kid-only views.
- Run the whole suite in well under 10 seconds locally (no real network, no
  real images, no real fixtures from disk).
- Make it trivial to run: `./manage.py test`.

## Non-goals (v1)
- Load / concurrency tests. Single LAN process; SQLite serializes writes.
- Visual regression / accessibility tooling. Manual mobile review per PLAN.md.
- 100% line coverage. Coverage as a number is not a goal.

## Tooling
- **Django's built-in test runner** (`./manage.py test`) using
  `django.test.TestCase` (transactional rollback per test — fast and clean).
- **`Client`** for view-level tests (`self.client.login`, `self.client.post`,
  follow redirects, assert template + content).
- **Playwright + Chromium** for the e2e suite. Tests subclass
  `StaticLiveServerTestCase` so Django spins up a real server on a random
  port; Playwright drives a headless browser against it. Sync API, one
  browser per class, fresh `BrowserContext` per test.
- **No pytest, no factories, no fixtures-on-disk for v1.** A small
  `setUpTestData` factory per test class keeps things explicit and fast.
  Re-evaluate `factory_boy` only if setup boilerplate grows painful.
- **No mocking of the database or auth.** Tests hit SQLite in-memory via the
  default test database — Django swaps in a fresh DB automatically.
- **Images:** use `SimpleUploadedFile` for any avatar/store-image tests so
  nothing touches the real filesystem; override `MEDIA_ROOT` to a tmp dir
  with `@override_settings` if needed.
- **Test-only fast hasher.** `settings.py` swaps to `MD5PasswordHasher` when
  `"test" in sys.argv` so the unit suite stays sub-second.

## Per-app coverage

Each app gets a `tests/` package (`tests/__init__.py` + one file per surface).
Below is the minimum set of tests; add more as bugs are found.

### `families/tests/`
- `test_user_model.py`
  - `create_parent` sets `role=parent`, hashes password, sets `username`.
  - `create_kid` sets `role=kid`, hashes PIN, leaves `username=None`.
  - `is_parent` / `is_kid` properties return the right thing.
- `test_auth_backend.py`
  - `KidPinBackend` returns the kid for correct (user_id, pin).
  - Returns `None` for wrong PIN, archived kid, parent user_id.
- `test_login_views.py`
  - Profile picker lists active kids only (archived hidden).
  - Parent login: valid creds → redirect to `/`; wrong creds → form re-renders
    with error; a kid trying parent login is rejected.
  - Kid PIN login: valid PIN logs in; wrong PIN re-renders error.
  - `logout` clears session and redirects to picker.
- `test_user_admin.py`
  - Kid blocked from accessing `/users/`, redirected to `/`.
  - Parent can create a kid (PIN required on create) and a parent
    (username + password required on create).
  - Edit form treats credentials as optional ("leave blank to keep").
  - Role-aware validation: kid form missing PIN on create → form error;
    parent form missing username on create → form error.
  - Archive toggles `is_active`. **Last active parent cannot be archived**
    — assert error message and DB unchanged.
  - Archived kid does not appear in profile picker but historical awards
    still resolve (FK with `PROTECT`).

### `points/tests/`
- `test_services.py`
  - `balance_for` = sum of awards.
  - `balance_for` subtracts only `APPROVED` and `FULFILLED` purchases
    (`PENDING` and `DENIED` do not count).
  - `pending_total_for` sums only `PENDING`.
  - `available_balance_for` = balance − pending_total.
  - Empty cases (no awards, no purchases) return 0, not `None`.
- `test_award_view.py`
  - Kid is forbidden from `/points/award/`.
  - Parent posts a valid award → `PointAward` row exists with right
    `kid`, `awarded_by`, `amount`, `reason`; balance updates.
  - Invalid form (amount=0, missing reason, non-kid as target) re-renders
    with errors and creates nothing.
- `test_home_views.py`
  - Parent home lists all active kids with current balance.
  - Pending-count badge reflects the real count.
  - Kid home shows kid's own balance and merged history (awards +
    approved/fulfilled purchases), newest first. A kid cannot see another
    kid's history.

### `store/tests/`
- `test_item_model.py`
  - `is_limited` matches type.
  - `in_stock` is True for repeatable, True for limited with stock > 0,
    False for limited with stock = 0.
- `test_admin_crud.py`
  - Kid blocked from `/store/admin/`.
  - Parent can create a repeatable item (no stock required).
  - Parent creating a `limited` item with no `stock_remaining` → form error
    ("Limited-stock items need a stock count.").
  - Archiving toggles `is_active`. Archived items don't appear in
    `/store/` browse but the `StoreItem` row remains for historical
    `PurchaseRequest` rows.
- `test_browse.py`
  - Parent blocked from `/store/`.
  - Browse shows only `is_active=True` items.
  - Pending requests block pinned above grid.
  - Item button is disabled when cost > available balance (assert markup),
    and when limited item is sold out.

### `purchases/tests/`
- `test_request_flow.py`
  - Parent blocked from `/purchases/request/<id>/`.
  - Successful request: status=PENDING, `cost_at_request = item.cost`,
    no balance/stock change.
  - **Price locking**: change `item.cost` after request; the pending
    `cost_at_request` is unchanged; balance math uses the locked value.
  - **Overdraft block**: kid with balance B has pending requests summing
    to P; a new request for X is rejected when X > B − P, with the
    error message visible in the redirect.
  - Sold-out limited item is rejected at request time with a message.
  - Inactive item is not requestable (404).
- `test_approval_flow.py`
  - Kid blocked from `/purchases/queue/` and the action endpoints.
  - Queue shows pending and approved buckets correctly.
  - Approve: status → APPROVED, `decided_by` = parent, `decided_at` set,
    balance drops by `cost_at_request`, stock decrements for limited items.
  - Approve a request whose kid no longer has enough points (because an
    earlier request was approved first) → fails with a clear error; no
    state change.
  - **Stock decrement timing**: with stock = 1 and two pending requests
    for the same item, the first approval succeeds (stock → 0), the second
    is rejected ("out of stock").
  - **Denied requests do not consume stock**: deny a request for a
    limited item; stock unchanged.
  - Deny: status → DENIED, no balance/stock change. Cannot deny something
    already approved.
  - Fulfill: only valid from APPROVED → FULFILLED; cannot fulfill a
    pending or denied request.
  - Re-approving / re-denying / double-fulfilling produce a clear error
    and no second state change (idempotency at the user level).

### `e2e/`

End-to-end browser tests live in a top-level `e2e/` package (not in
`INSTALLED_APPS` — invoke explicitly with `./manage.py test e2e` so the
fast unit suite stays fast).

- `e2e/base.py` — `PlaywrightTestCase` base class. Launches Chromium per
  class, fresh `BrowserContext` per test, viewport sized to a phone
  (414×896, 2x scale) so screenshots reflect the mobile-first design.
  Helpers: `login_parent`, `login_kid`, `switch_user`, `url(path)`,
  `shot(label)` (saves `NN_label.png` under
  `screenshots/<TestClass>/<test_name>/`).
- `e2e/test_happy_path.py` — `HappyPathTests.test_full_purchase_cycle`:
  walks parent → award → switch to kid → request item → switch back to
  parent → approve → fulfill → kid sees updated history. 15 screenshots
  cover every state transition.
- `e2e/test_admin_surfaces.py` — surfaces not on the happy path:
  - `StoreAdminTests`: list, empty add form, limited-stock validation
    error, list after create.
  - `UserAdminTests`: list, add-user form with role-aware credential
    toggle (kid PIN → parent password), last-active-parent guard error.
  - `ErrorStateTests`: wrong PIN, wrong parent password, kid store with
    both "Not enough points" and "Sold out" disabled buttons.

Screenshots land in `screenshots/` (gitignored). Flip through them in
order to validate UI changes visually.

## Shared test helpers

Put in `families/tests/factories.py` (plain functions, no factory_boy):
- `make_parent(name="Mom", username="mom", password="pw")`
- `make_kid(name="Alex", pin="1234")`
- `make_item(name, cost, type="repeatable", stock=None)`
- `award(kid, amount, by, reason="ok")`
- `login_as(client, user)` — uses `client.force_login(user)` to skip the
  PIN/password dance in non-auth tests.

Use `setUpTestData(cls)` to build the family once per test class; instance
methods can mutate freely thanks to per-test transaction rollback.

## Running

```sh
.venv/bin/python manage.py test                       # everything (~6s)
.venv/bin/python manage.py test families points store purchases  # unit only (<1s)
.venv/bin/python manage.py test e2e                   # e2e only (~5s)
.venv/bin/python manage.py test purchases             # one app
.venv/bin/python manage.py test purchases.tests.test_approval_flow  # one file
.venv/bin/python manage.py test e2e.test_happy_path   # one workflow
.venv/bin/python manage.py test --keepdb              # faster reruns once schema is stable
```

Default `./manage.py test` auto-discovers `e2e/` along with the app suites,
so a single command runs everything. For tight iteration on non-UI code,
list the app names explicitly to skip the browser tests.

Before running e2e for the first time, install the browser:
`.venv/bin/playwright install chromium`.

A `--parallel` run is fine for the unit suite but not for e2e (single
shared browser).

## When to add a test
- **Always** when fixing a bug — write the failing test first, then the fix.
- **When changing behavior in `services.py`, the approval transaction, or
  the user/auth admin** — these are the highest-blast-radius parts.
- **Not** for typo fixes, copy changes, or pure styling.

## Future (not v1)
- GitHub Actions running `manage.py test` (and optionally e2e) on push
  if/when this lives in a shared repo.
- Coverage report via `coverage run` — useful as a discovery tool, never as
  a gate.
- Visual regression: compare screenshots across runs (e.g. `pixelmatch`)
  once the UI is stable enough that diffs are signal, not noise.
