-- REFERENCE ONLY — not applied by the app or any tooling.
-- The Alembic migrations under migrations/versions/ are the source of truth
-- for schema changes (run via `flask db upgrade`). This file is kept as a
-- human-readable snapshot of the schema and must be updated manually if it
-- drifts from the migrations.
--
-- `phone`/`whatsapp` columns store Fernet ciphertext (TEXT), encrypted at the
-- application layer (see app/crypto.py) — never plaintext at rest. See
-- docs/DATA_ACCESS_POLICY.md for the full public/authenticated/private field
-- classification.

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL, -- one-way hash only, never encrypted/decrypted
    role VARCHAR(40) NOT NULL DEFAULT 'customer',
    name VARCHAR(255) NOT NULL,
    phone TEXT, -- encrypted at rest
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS providers (
    id SERIAL PRIMARY KEY,
    profile_code VARCHAR(64) UNIQUE NOT NULL,
    user_id INTEGER REFERENCES users(id),
    first_name VARCHAR(120) NOT NULL,
    last_name VARCHAR(120),
    phone TEXT, -- encrypted at rest
    whatsapp TEXT, -- encrypted at rest
    city VARCHAR(120),
    state VARCHAR(120),
    latitude DOUBLE PRECISION,
    longitude DOUBLE PRECISION,
    hourly_rate NUMERIC(10, 2),
    experience_years INTEGER DEFAULT 0,
    jobs_completed INTEGER DEFAULT 0,
    rating DOUBLE PRECISION DEFAULT 0,
    reviews_count INTEGER DEFAULT 0,
    verified BOOLEAN DEFAULT FALSE,
    availability VARCHAR(80) DEFAULT 'available',
    profile_photo_url TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS services (
    id SERIAL PRIMARY KEY,
    name VARCHAR(160) NOT NULL,
    slug VARCHAR(160) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS provider_services (
    id SERIAL PRIMARY KEY,
    provider_id INTEGER NOT NULL REFERENCES providers(id),
    service_id INTEGER NOT NULL REFERENCES services(id),
    sub_services TEXT
);

CREATE TABLE IF NOT EXISTS locations (
    id SERIAL PRIMARY KEY,
    city VARCHAR(160) NOT NULL,
    state VARCHAR(160) NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    longitude DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS bookings (
    id SERIAL PRIMARY KEY,
    customer_id INTEGER NOT NULL REFERENCES users(id),
    provider_id INTEGER NOT NULL REFERENCES providers(id),
    service_id INTEGER NOT NULL REFERENCES services(id),
    status VARCHAR(40) DEFAULT 'pending',
    scheduled_at TIMESTAMP,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS reviews (
    id SERIAL PRIMARY KEY,
    provider_id INTEGER NOT NULL REFERENCES providers(id),
    customer_id INTEGER NOT NULL REFERENCES users(id),
    booking_id INTEGER REFERENCES bookings(id),
    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_providers_city ON providers(city);
CREATE INDEX IF NOT EXISTS idx_providers_state ON providers(state);
CREATE INDEX IF NOT EXISTS idx_provider_services_provider ON provider_services(provider_id);
CREATE INDEX IF NOT EXISTS idx_provider_services_service ON provider_services(service_id);
CREATE INDEX IF NOT EXISTS idx_bookings_customer ON bookings(customer_id);
CREATE INDEX IF NOT EXISTS idx_bookings_provider ON bookings(provider_id);
