# Tedile

A local service-provider marketplace app — find and book verified plumbers,
electricians, tutors, and other local professionals near you.

Built as a companion project to BengalLearningCenter, following the same
production-ready structure (Flask + SQLAlchemy + S3 + Capacitor mobile
wrapper), but for a different domain: connecting customers with local
service providers.

## Features

- Customer, provider, and admin roles with hashed-password authentication
- Provider search by service, keyword, price range, verified-only, and
  distance (haversine radius search), with configurable sort order
- Booking workflow: customers request a provider, providers confirm/complete
  bookings
- Admin verification workflow for providers
- Ratings/reviews model for completed bookings
- iOS and Android app shells via Capacitor, wrapping the same web app
- Restricted public API responses, PII encryption at rest, and authorization
  gating for contact details — see
  [docs/DATA_ACCESS_POLICY.md](docs/DATA_ACCESS_POLICY.md)

## Tech stack

- Python 3.12+, Flask, Flask-SQLAlchemy
- PostgreSQL in production, SQLite for local development
- AWS S3 for uploaded files (provider photos, documents)
- Capacitor for the iOS/Android wrapper apps

## Project structure

```text
Tedile/
├── app.py                  # entrypoint
├── config.py                # env-driven configuration, no hardcoded secrets
├── requirements.txt
├── render.yaml               # Render deployment config
├── database/
│   ├── schema.sql            # reference-only snapshot; migrations/ is the source of truth
│   ├── seed.py                # seeds services + sample locations only
│   └── import_providers.py      # one-time/import-source ingestion tool
├── data/
│   └── imports/               # dated, ignored historical import sources
├── migrations/                 # Alembic revision history (Flask-Migrate)
├── app/
│   ├── __init__.py            # app factory
│   ├── extensions.py           # SQLAlchemy instance
│   ├── models/                  # Provider, Service, ProviderService, Location, Booking, Review, User
│   ├── routes/                   # auth, customer, provider, admin, api (search/geocode)
│   └── services/                  # auth_service, search_service, geo_service, s3_service, storage_service
├── static/
├── templates/
├── tests/
└── mobile/                          # Capacitor iOS/Android wrapper
```

## Run locally

```bash
cd Tedile
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in values as needed; defaults work for local dev
flask db upgrade         # applies Alembic migrations (creates the schema)
python -m database.seed  # loads service categories + sample cities
python app.py
```

Then open http://127.0.0.1:5001

## Database migrations

Schema changes are managed exclusively through Flask-Migrate/Alembic under
`migrations/`. `db.create_all()` is intentionally not used.

```bash
flask db upgrade                       # apply all pending migrations
flask db migrate -m "describe change"   # generate a new migration after editing models
flask db current                        # show applied revision
```

`database/schema.sql` is kept as a reference-only snapshot; it is not applied
by any tooling and must be updated by hand if it drifts from the migrations.

## Configuration

All secrets and connection info come from environment variables — nothing is
hardcoded:

```env
SECRET_KEY=your-long-random-secret
FLASK_DEBUG=false
APP_ENV=production
DATABASE_URL=postgresql://user:password@host:5432/tedile
AWS_REGION=ap-south-1
S3_BUCKET_NAME=tedile-app
AWS_ACCESS_KEY_ID=your_access_key
AWS_SECRET_ACCESS_KEY=your_secret_key
```

If `SECRET_KEY` is unset in development, a random key is generated per
process start (fine for local dev, never for production — `ProductionConfig`
raises an error if `SECRET_KEY` is missing).

## Data model notes

PostgreSQL is the single source of truth for live Tedile provider, service,
booking, and account data. JSON files under `data/imports/` are historical
ingestion inputs only. They are not served, read by runtime search APIs, or
used as a provider database. Future provider changes must use authenticated
Tedile APIs/admin workflows.

This app does **not** ship with any scraped or third-party provider data.
`database/seed.py` only inserts service categories (Plumber, Electrician,
etc.) and a handful of reference city coordinates so search has something to
query against locally. Real provider records are created through normal
signup/onboarding (`Provider` rows linked to a `User` with role `provider`).

- `providers` — one row per provider
- `services` — service categories (Plumber, Electrician, ...)
- `provider_services` — many-to-many join, since one provider can offer
  multiple services
- `locations` — lightweight local "geocoder" table for resolving a city name
  to coordinates
- `bookings` — customer → provider requests with a status lifecycle
- `reviews` — post-booking ratings

## Mobile apps (iOS/Android)

See [mobile/README.md](mobile/README.md). The mobile wrapper uses Capacitor to
load the same Flask web app inside a native shell, exactly like
BengalLearningCenter's mobile setup, just re-branded and pointed at Tedile's
backend.

## Tests

```bash
pytest
```
