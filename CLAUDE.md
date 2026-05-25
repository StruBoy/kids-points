# Notes for Claude

Single-family Django app for tracking and spending kid behavior points.
See `README.md` for the human pitch and `PLAN.md` for design decisions.

## Stack at a glance
- Django 5.2, Python 3.12+, SQLite
- Server-rendered Django templates + HTMX + Tailwind, both via CDN (no
  build step). Don't introduce a JS framework or a CSS pipeline without
  asking.
- Custom `User` model in `families` — wired up before the very first
  `migrate`, do not "fix" this by switching to the default user.

## App layout (5 apps + e2e)
- `families` — `User`, `KidPinBackend`, login views, user admin, decorators
- `points` — `PointAward`, award form, parent/kid home views, balance services
- `store` — `StoreItem`, parent CRUD, kid browse
- `purchases` — `PurchaseRequest`, request + approval/deny/fulfill flow
- `web` — `base.html`, root redirect
- `e2e` — Playwright tests (not in `INSTALLED_APPS`; discovered via project-root scan)

## Hard rules (these matter)

1. **`PointAward` and `PurchaseRequest` are immutable once created.** Bug fixes
   happen via a new corrective entry, not by editing history. If you find
   yourself reaching for `.save()` on these to change `amount` or
   `cost_at_request`, stop and rethink.
2. **Price locking.** `PurchaseRequest.cost_at_request` snapshots the item
   cost at request time. Balance math reads `cost_at_request`, never
   `item.cost`. Changing an item's price must not affect pending or past
   requests.
3. **Stock decrements on approval, not on request.** Otherwise denied
   requests would leak stock. The approval path lives in
   `purchases/views.py:approve` and uses `transaction.atomic` +
   `select_for_update`. Keep it that way.
4. **At least one active parent must always exist.** The guard is in
   `families/views.py:user_archive`. Don't bypass it from new code paths.
5. **Balance is computed on read** via `points.services.balance_for` /
   `available_balance_for`. Don't add a denormalized balance field — it
   isn't needed at family scale and would invite drift.
6. **PIN auth is intentionally low-security.** 4-digit PIN, hashed with
   Django's hashers. It protects against sibling tampering, not real
   attackers. Don't add rate limiting, lockouts, or 2FA — out of scope.

## Auth quirks
- Parents auth via `ModelBackend` (username + password).
- Kids auth via `families.auth.KidPinBackend` which takes `user_id` + `pin`
  kwargs to `authenticate()`. Both backends are in
  `AUTHENTICATION_BACKENDS`; unrecognized kwargs make the other backend
  return `None`, so they don't fight.
- Two helper decorators in `families/decorators.py`: `parent_required` and
  `kid_required`. Use these on every view — don't reach for
  `@login_required` alone.

## Settings quirks
- `if "test" in sys.argv: PASSWORD_HASHERS = [MD5]` — keeps the unit suite
  sub-second. Don't remove.
- `MEDIA_ROOT` and `STATIC_ROOT` are explicitly served in DEBUG from
  `kidspoints/urls.py`. Production deploy will need a real static-files
  setup (TBD; see PLAN.md).

## Templates
- One root `templates/base.html` with header (avatar + "Switch user") and
  flash messages.
- Tailwind classes inline; no design system / component library.
- All layouts are mobile-first (viewport widths around 375–414px). When
  adding new pages, screenshot them in the e2e suite at 414×896 to keep
  visual coverage honest.

## Tests
- Unit tests live in each app's `tests/` package.
- E2E tests live in `e2e/` (Playwright + `StaticLiveServerTestCase`).
  Base class is `e2e.base.PlaywrightTestCase` — use its helpers
  (`login_parent`, `login_kid`, `switch_user`, `shot`).
- `DJANGO_ALLOW_ASYNC_UNSAFE=true` is set at module import in
  `e2e/base.py` because Playwright's sync API runs an event loop in a
  worker thread that trips Django's safety check on DB flush. Don't
  remove unless you're using async Playwright.
- Use the factories in `families/tests/factories.py`
  (`make_parent`, `make_kid`, `make_item`, `award`, `request_item`,
  `login_as`) — don't hand-roll users in tests.
- When asserting against HTML, watch out for HTML-escaped apostrophes
  (`&#x27;`) — keep test strings apostrophe-free or assert against the
  escaped form.
- When using Playwright `get_by_text`, prefer `exact=True` or
  `get_by_role(...)` to avoid strict-mode violations when the text
  appears in flash messages AND content.

## Commands you'll actually use

```sh
.venv/bin/python manage.py runserver
.venv/bin/python manage.py seed_family --reset   # wipe + reseed demo data
.venv/bin/python manage.py test                  # all 90 tests, ~6s
.venv/bin/python manage.py test e2e              # browser tests only
.venv/bin/python manage.py makemigrations <app>  # after model changes
```

## What NOT to do without asking

- Don't add a denormalized balance cache or a "current balance" column.
- Don't add `created_at`/`updated_at` triggers, audit logging, or "undo"
  features — immutability + corrective entries is the v1 design.
- Don't switch SQLite for Postgres "to be safe" — single-family scale.
- Don't introduce a frontend build tool (Vite, esbuild, Tailwind CLI) or
  a JS framework. HTMX + CDN Tailwind is deliberate.
- Don't add OAuth, password reset emails, signup flows, or multi-family
  support — all out of scope per PLAN.md.
- Don't add fixtures-on-disk for tests. Use the factory functions.
