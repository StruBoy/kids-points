# Kids Points App — Plan

## Context
We're building a web app for a single family to track and spend "good behavior" points for kids. Parents award points (with a reason), kids see their balance and history, and kids spend points in a virtual store of items the parents curate. The goal is a simple, positive system the family can actually use day-to-day on phones and tablets around the house. The repository is empty — this is a greenfield build.

## Core Features
1. **Award points (parent)** — Parent picks a kid, enters a positive point amount and a reason, submits. Award is recorded immutably with timestamp and granting parent.
2. **View balance & history (kid)** — Kid sees their current balance and a chronological feed of awards (amount + reason + date) and approved purchases (deductions).
3. **Request items from store (kid)** — Kid browses store, taps an item to request it. Request enters `pending` state; points are *not* deducted yet.
4. **Approve / deny / fulfill purchases (parent)** — Parent reviews pending requests. On approve: points deducted, request moves to `approved` then `fulfilled` once delivered. On deny: nothing deducted, request closed.
5. **Manage store (parent)** — Parent CRUDs items: name, description, cost, optional image, type (repeatable vs limited-stock), stock count for limited items, active/archived flag.
6. **Manage users (parent)** — Parent CRUDs users of either role. Create / edit / archive parents and kids; set or reset a parent's password or a kid's 4-digit PIN; upload/change an avatar; change display name and role. At least one active parent must exist at all times.

## Out of Scope (explicit non-goals for v1)
- Subtracting points / negative entries (award-only)
- Recurring or automated point rules
- Goal-setting / progress bars toward a target item
- Sibling leaderboards
- Multi-family / signup / billing
- Push notifications

## Users & Auth
- **Single family, no public signup.** App is seeded with one family's users.
- **Parents:** username + password. Typed rarely; small number of accounts.
- **Kids:** profile picker (avatar + name) → 4-digit PIN. PIN is intentionally low-security — it protects against sibling tampering, not real attackers.
- Sessions persist ~30 days on a device. A "switch user" control is always visible in the header.

## Data Model (Django models, sketch)
- `User(AbstractBaseUser)` — `name`, `role` (`parent` | `kid`), `avatar`, `password` (Django's hashed field, holds password for parents and PIN for kids). One custom field is enough; reuse Django's hashers for both.
- `PointAward` — `kid` (FK User), `awarded_by` (FK User), `amount` (PositiveIntegerField), `reason` (CharField), `created_at`.
- `StoreItem` — `name`, `description`, `image` (ImageField, optional), `cost` (PositiveIntegerField), `type` (`repeatable` | `limited`), `stock_remaining` (nullable PositiveIntegerField), `is_active`, `created_at`.
- `PurchaseRequest` — `kid` (FK User), `item` (FK StoreItem), `cost_at_request` (PositiveIntegerField), `status` (`pending` | `approved` | `denied` | `fulfilled`), `requested_at`, `decided_at` (nullable), `decided_by` (FK User, nullable).

**Balance** = `SUM(point_awards.amount for kid) − SUM(purchase_requests.cost_at_request where status in (approved, fulfilled))`. Computed on read — trivial at family scale; add caching later if ever needed.

## Key Behaviors & Edge Cases
- **Price locking:** A pending/approved request locks the price at `cost_at_request`. Later edits to the item's cost don't change historical requests.
- **Stock decrement timing:** Limited-stock items decrement on **approval**, not on request — otherwise denied requests would leak stock. Parent UI shows live remaining stock.
- **Overdraft prevention:** A kid cannot submit a request if approving it would push their balance below zero (accounting for other pending requests). Block at request time with a clear message.
- **Immutability:** Awards and purchase requests are immutable once created. Corrections happen via a new entry (corrective entries are not in v1; we'll add only if a real mistake comes up).

## UX Surfaces
- **Kid home:** big balance number, "Store" button, "My history" feed (newest first).
- **Kid store:** grid of items with cost + request button; their pending requests pinned at top.
- **Parent home:** list of kids with balances, "Give points" CTA, badge showing count of pending requests.
- **Parent give-points screen:** kid picker, amount, reason, submit.
- **Parent store admin:** item list with add / edit / archive.
- **Parent requests queue:** pending list (approve/deny), approved list (mark fulfilled).
- **Parent user admin:** list of all users (parents and kids), add new user (role picker drives whether the form shows a password field or a 4-digit PIN field), edit existing user (name, avatar, role, reset password/PIN), archive (soft delete via `is_active`). Archived users cannot log in and don't appear in the profile picker, but their historical awards and purchases remain intact.

Mobile-first layouts; all primary actions reachable with one thumb on a phone.

## Tech Stack
- **Django (latest stable) + Python 3.12+** — server-rendered web app using Django templates and the built-in admin where it earns its keep.
- **SQLite** — Django's default; a single file on the home server's disk. Backups are a periodic file copy. Plenty for one family; can swap to Postgres later by changing settings.
- **HTMX + Tailwind** for interactive bits (request item, approve, mark fulfilled) without a SPA build step. Keeps the frontend minimal and Django-native.
- **Auth:** custom over Django's session framework. Parents use `django.contrib.auth` (username + password). Kids use a custom backend: profile picker posts a `user_id` + 4-digit PIN; PIN stored via Django's password hashers. The kid login view bypasses the username field entirely.
- **Store images:** uploaded to `MEDIA_ROOT` on the server's disk; served by Django in dev and by the front-end web server in production.
- **Hosting:** local LAN server inside the home. Concrete details (machine, reverse proxy, process manager, TLS) deferred — to be specified before deploy. Plan assumes a single long-running Python process (gunicorn or similar) behind a reverse proxy, with SQLite and `MEDIA_ROOT` on a path that's included in the home backup routine.

## Project Layout (Django apps)
- `families` — custom `User` model, seeding/management commands, **user admin views** (list, create, edit, archive — accessible to parents only).
- `points` — `PointAward` model, award form, kid history view.
- `store` — `StoreItem` model, parent CRUD, kid browse view.
- `purchases` — `PurchaseRequest` model, request flow, parent approval queue, fulfill action.
- `web` — base templates, navigation, profile picker, "switch user".

User admin is built as in-app views (not Django's `/admin/`) so it shares the same look-and-feel and is usable on a phone. The form switches between a password field (parents) and a 4-digit PIN field (kids) based on the selected role.

## Build Order
1. Scaffold Django project + the five apps above; custom `User` model wired up from the start (must be done before first `migrate`); base template with Tailwind + HTMX; SQLite settings.
2. Seed management command for one family (two parents, two kids, a few demo store items).
3. Auth: parent login view, kid profile picker view, kid PIN login view + custom auth backend, "switch user" link, session config.
4. Award-points form (parent) + kid history view (read-only list of awards and approved purchases, newest first).
5. Store admin CRUD (parent) — list, create, edit, archive; image upload to `MEDIA_ROOT`.
6. User admin (parent) — list, create, edit, archive parents and kids; role-aware form (password vs PIN); guard against archiving the last active parent.
7. Kid store browse + request flow with overdraft block at submit time and price-locking via `cost_at_request`.
8. Parent approval queue + approve / deny / mark-fulfilled actions, wrapped in a transaction that decrements stock on approval.
9. Polish: avatars, empty states, friendly error messages, mobile layout review at 375px.

## Verification
- Seed two parents + two kids and a handful of store items (mix of repeatable and limited-stock).
- Walk the golden path end-to-end: parent awards points → kid sees them in history → kid requests an item → parent approves → balance decreases → parent marks fulfilled.
- Edge cases to exercise manually:
  - Request that would overdraw balance is blocked at request time.
  - Limited-stock item: cannot be approved once stock hits zero; denied requests don't consume stock.
  - Price change on an item does not change a pending request's locked price.
  - Kid sees only their own data; switching users requires PIN re-entry.
  - User admin: a parent can add a new kid (with PIN) and a new parent (with password), reset either credential, and archive a user. Trying to archive the last active parent is blocked with a clear message. Archived users disappear from the profile picker but their past awards/purchases still display in history.
- Visual check at 375px viewport (small phone) and tablet width on every screen.
