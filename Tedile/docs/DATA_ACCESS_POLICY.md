# Tedile Data Access Policy

This document defines the security boundary between Tedile's backend/database
and any client (browser, mobile app, or third party). It classifies every
model field as **Public**, **Authenticated**, or **Private**, and states how
each boundary is enforced in code. This is the reference for any future
endpoint: if a field isn't listed here as Public, it must not appear in a
public API response.

## Core principles

1. **The browser/mobile app never talks to PostgreSQL directly.** All access
   goes through Flask routes in `app/routes/`, using server-side
   `DATABASE_URL` credentials that never leave the server process.
2. **PostgreSQL is the single source of truth for live data.** Files under
   `data/imports/` are dated historical ingestion sources only. They are not
   served, loaded by runtime APIs, or used as a provider database.
3. **Public search/browse endpoints return a restricted DTO**, not the full
   ORM row. See `Provider.to_public_dto()` in
   [app/models/provider.py](../app/models/provider.py) and its use in
   [app/services/search_service.py](../app/services/search_service.py).
4. **Sensitive fields are gated by an explicit authorization rule**, not a
   client-side toggle. Contact details are only returned by
   `GET /customer/providers/<profile_code>/contact` (see
   [app/routes/customer.py](../app/routes/customer.py)), and only when the
   requesting customer has a `confirmed` or `completed` `Booking` with that
   provider. Removing a field from a JSON response client-side is not
   sufficient and is not how this is implemented — the server itself decides
   what to serialize.
5. **PII is encrypted at rest**; passwords are one-way hashed and never
   encrypted/decrypted (see "Encryption" below).
6. **No provider data is hard-coded into frontend/static/mobile code.**
   `static/app.js` and the mobile shell only ever call `/api/...` endpoints;
   all provider records come from the database via `database/seed.py`
   (reference data only, no real providers) or real signups.
7. **HTTPS is enforced in production** via a `before_request` redirect in
   `app/__init__.py` (skipped in dev/debug and for `/health`).

## Field classification

### `Provider`

| Field | Classification | Where exposed |
|---|---|---|
| `profile_code` | **Public** (as the DTO's `"id"`) | `to_public_dto()` — the public identifier; the real integer primary key (`id`) is never sent to clients |
| `name`, `city`, `state` | Public | `to_public_dto()` |
| `hourly_rate`, `experience_years`, `jobs_completed`, `rating`, `reviews_count`, `verified`, `availability`, `profile_photo_url` | Public | `to_public_dto()` |
| `distance_bucket` (computed) | Public | coarse value such as `under_5km` or `10_25km`; exact distance is computed server-side and never serialized |
| `latitude`, `longitude` (exact) | **Private** | never serialized to any client; used only in-memory server-side for the haversine distance calculation |
| `phone`, `whatsapp` | **Private** | encrypted at rest (`EncryptedString`); only returned by `to_contact_dto()` from the authorization-gated `/customer/providers/<profile_code>/contact` endpoint |
| `id` (integer primary key) | **Private** | never serialized in any client-facing response; used only for internal joins/FKs |
| `user_id` | Private | internal FK only |

### `User`

| Field | Classification | Where exposed |
|---|---|---|
| `id`, `name`, `role` | **Authenticated** (own session only) | `to_session_dict()` — the only representation ever placed in the Flask session cookie |
| `email` | **Private** | never placed in the session cookie or any API response; used only for login lookup server-side |
| `phone` | **Private** | encrypted at rest; never returned to the client in current routes |
| `password_hash` | **Private, never decrypted** | one-way hash (`werkzeug.security`); there is no code path that reads or reverses it — only `check_password_hash()` compares |

Flask's default session is a signed-but-client-readable cookie (not
server-side storage), so anything placed in `session["user"]` is visible to
the browser. `to_dict()` (full, including email/phone) exists only for
server-side internal use and must never be assigned to `session[...]` or
returned from a route directly.

### `Booking`

| Field | Classification | Where exposed |
|---|---|---|
| `reference`, `status`, `scheduled_at`, `notes` | Authenticated (owner only) | Explicit customer/provider booking DTOs; the reference is an opaque HMAC-derived value |
| `customer_id`, `provider_id`, `service_id` (internal FKs) | **Private** | Never serialized in booking responses; server-side joins use them internally. Booking creation accepts a provider profile code and service slug. |

### `Service`, `Location`

safe to expose in full via `/api/services` and `/api/search/geocode`.
Public reference data only (service categories, city coordinates) — no PII.
`/api/services` exposes only `name` and `slug`; database service IDs are private.
`/api/search/geocode` exposes seeded locality coordinates, not provider
coordinates.

`GET /api/providers/<profile_code>` is the public provider profile endpoint and
returns only `Provider.to_public_dto()`.

### `Review`

Not yet exposed via any route. If/when a reviews endpoint is added, `comment`
and `rating` are public; `customer_id` must not be serialized (show a display
name only if the reviewer opts in).

## Encryption at rest

- `Provider.phone`, `Provider.whatsapp`, and `User.phone` use
  `app.crypto.EncryptedString`, a SQLAlchemy `TypeDecorator` that encrypts
  with [Fernet](https://cryptography.io/en/latest/fernet/) (AES-128-CBC +
  HMAC) before writing to the database and decrypts transparently when read
  through the ORM inside an app context. The database only ever stores
  ciphertext.
- The encryption key is `ENCRYPTION_KEY` (see `.env.example`). In production,
  `ProductionConfig` raises at startup if it is unset — an ephemeral/rotating
  key would make previously-encrypted data permanently unreadable.
- **`email` is intentionally not encrypted** at the application layer: it is
  used for equality lookups during login (`User.query.filter_by(email=...)`),
  and Fernet ciphertext is non-deterministic, so it cannot be queried by
  equality without a separate blind-index/HMAC column. Known follow-up: add
  a deterministic HMAC "email_lookup_hash" column for indexed lookups while
  storing the email itself encrypted or relying on PostgreSQL's
  transparent-data-encryption / `pgcrypto` at the storage layer.
- **Passwords are never encrypted or decrypted.** `User.password_hash` is a
  one-way hash produced by `werkzeug.security.generate_password_hash` and
  verified with `check_password_hash`. There is no decrypt path.

## Authorization rule for contact details

`GET /customer/providers/<profile_code>/contact`:

1. Requires an authenticated session with role `customer` (`login_required`).
2. Looks up the `Provider` by `profile_code` (never by internal `id`).
3. Requires an existing `Booking` for `(customer_id, provider_id)` with
   `status` in `("confirmed", "completed")`.
4. Only then returns `Provider.to_contact_dto()` (`name`, `phone`,
   `whatsapp`), decrypted at that point.

Provider search must never leak contact details up front — they are only
released after an authorized business action (a confirmed booking), enforced
entirely server-side.

## HTTPS

`app/__init__.py` registers a `before_request` hook that 301-redirects any
non-HTTPS request to HTTPS when the app is not running in debug mode (dev is
exempt so `http://127.0.0.1:5001` keeps working locally). `SESSION_COOKIE_SECURE`
is also `True` in `ProductionConfig`, so session cookies are never sent over
plain HTTP in production. Render terminates TLS at the edge and forwards
`X-Forwarded-Proto`, which this hook checks.

## CSRF

All state-changing browser/session routes require a server-generated token in
the session and a matching form field or `X-CSRFToken` header. This includes
login, signup, logout, customer booking creation, provider availability and
booking-status changes, and admin verification. The browser templates render
the token server-side; JavaScript-only hiding is not used.

## Known follow-ups (not yet implemented)

- Deterministic/blind-index lookup for encrypted `email`, so it can also be
  encrypted at rest without breaking login.
- A dedicated reviews endpoint should reuse this same public/private
  separation before it's built.
- Rate limiting / abuse protection on `/api/search/providers` and the
   contact-reveal endpoint (currently relies on session auth + business-rule
   gating only).
- A production-safe PostgreSQL integration-test workflow; current tests are
   deliberately guarded to use only in-memory SQLite.
