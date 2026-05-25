# Kids Points

A web app for a single family to track and spend "good behavior" points for
kids. Parents award points with a reason; kids spend them in a virtual store
of items the parents curate. Designed to run on a small server inside the
home and be used from phones and tablets around the house.

## Features

**Parents can**
- Award points to a kid with a reason.
- Curate a store of items: name, description, image, cost, repeatable vs
  limited-stock.
- Review purchase requests: approve (points deducted, stock decremented for
  limited items), deny, or mark approved items as fulfilled.
- Manage users: add or edit parents (username + password) and kids
  (4-digit PIN), upload avatars, archive (soft-delete) users.

**Kids can**
- Sign in by tapping their avatar and entering their PIN.
- See their current balance and a chronological history of awards and
  approved purchases.
- Browse the store and request an item; the request waits for a parent to
  approve before points are deducted.

## Quick start

```sh
# 1. Create the venv and install dependencies
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/playwright install chromium   # only needed for the e2e tests

# 2. Build the database and seed a demo family
.venv/bin/python manage.py migrate
.venv/bin/python manage.py seed_family

# 3. Run it
.venv/bin/python manage.py runserver
```

Open http://127.0.0.1:8000/login/.

Seeded credentials (change them or re-seed with `--reset` once you're set up):
- Parents: `mom` / `password`, `dad` / `password`
- Kids: Alex (PIN `1234`), Sam (PIN `5678`)

## Tech stack

- Django 5.2 + Python 3.12+
- SQLite (single file on disk; back up by copying)
- Django templates + HTMX + Tailwind (both via CDN)
- Custom `User` model with two roles (`parent`, `kid`) and a custom
  PIN-based auth backend
- Pillow for image uploads (avatars, store items) to `MEDIA_ROOT`
- Playwright + Chromium for the end-to-end test suite

## Project structure

```
kidspoints/         Django project (settings, urls, wsgi)
families/           User model, custom auth backend, user admin
points/             PointAward model, award form, parent/kid home views, balance services
store/              StoreItem model, parent CRUD, kid browse
purchases/          PurchaseRequest model, request flow, approval queue
web/                Base templates, navigation, root redirect
e2e/                Playwright end-to-end tests
templates/          Project-wide templates (base.html)
PLAN.md             Design plan & architecture decisions
TESTING.md          Testing strategy & coverage map
```

## Development

```sh
.venv/bin/python manage.py test                # all 90 tests (~6s)
.venv/bin/python manage.py test families points store purchases  # unit only (<1s)
.venv/bin/python manage.py test e2e            # just the browser tests
.venv/bin/python manage.py seed_family --reset # wipe and re-seed
```

End-to-end tests save screenshots to `screenshots/` (gitignored), organized
by test class and method. Useful for visual review after UI changes.

## Hosting

Designed to run on a local LAN server inside the home behind a reverse
proxy (gunicorn or similar). SQLite and `MEDIA_ROOT` should live on a
disk that's included in the home backup routine. Concrete deploy
specifics (machine, reverse proxy, TLS) are TBD — see PLAN.md.

## Further reading

- [PLAN.md](PLAN.md) — feature scope, data model, key behaviors, build order
- [TESTING.md](TESTING.md) — testing strategy and what's covered
