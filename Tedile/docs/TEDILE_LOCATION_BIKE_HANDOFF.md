Tedile Location Feature --- Bike Developer Handoff

Purpose

This document explains the current Tedile customer Location feature and
how the Bike app should reuse it.

The core rule is:

Location is shared infrastructure. Bike is a consumer of that
infrastructure.

Do not create a separate, duplicate Location system for Bike unless a
documented technical requirement makes it necessary.

Git Checkpoint

Current branch:

Developement

Location work is checkpointed in:

7ce89ee  chore: establish booking feature migration chain
a7a40aa  feat: add customer location integration

Nothing was pushed as part of this checkpoint.

Location implementation commit

a7a40aa
feat: add customer location integration

Committed files:

app/models/booking.py
app/services/search_service.py
docs/LOCATION_INTEGRATION.md
templates/provider_profile.html

Migration foundation commit

7ce89ee
chore: establish booking feature migration chain

This contains the migration chain required by the current Location
migration.

Location Architecture

The customer is the actor who:

Selects a service.

Selects/searches a location.

Searches for providers near that selected location.

Selects a provider.

Creates a booking.

Provides/persists booking location when required.

Conceptually:

Customer
   |
   +--> Select service
   |
   +--> Select/search location
             |
             v
      Provider search
             |
             v
      Provider results
             |
             v
      Booking
             |
             v
      Customer booking location

A provider account should not be used as the customer search actor.

Search Location vs Customer GPS

These are intentionally separate concepts.

Search Location

The customer can manually select a location for provider discovery.

Example:

Customer is physically in another state
        |
        +--> selects Kolkata, West Bengal
        |
        +--> searches for a plumber

The search should use the selected Kolkata location.

Do not automatically replace the selected search location with the
device's current GPS.

This is particularly important for West Bengal location testing when the
tester is physically somewhere else.

Booking Location

When a booking requires the customer's location, the booking can store:

customer_latitude
customer_longitude
customer_location_label

These values are separate from the provider's location.

Database Migration

The Location migration is:

migrations/versions/d9e5f7a1b2c3_add_customer_booking_location.py

It adds nullable fields to bookings:

customer_latitude
customer_longitude
customer_location_label

Important migration dependency

The Location migration depends on:

c8d4e6f1a2b3

The complete existing chain is:

7c1f2e8a9b10  Review metadata
9b7e3f1a2c4d  Riders
a1c4e7d9b2f0  Bike rides
b7e2f4a8c1d3  Fare pricing
c8d4e6f1a2b3  Merge Fare + Review heads
d9e5f7a1b2c3  Customer booking location

Do not rewrite the Location migration's down_revision.

Do not create a duplicate Location migration to bypass the existing
history.

The dependency exists because the Location migration was created after
the other development migration branches had already been established.

Main Code Areas

The Location implementation is centered around:

app/models/booking.py
app/services/search_service.py

Detailed implementation/API information is documented in:

docs/LOCATION_INTEGRATION.md

Read that document before changing the Location contract.

Some Location-related behavior also exists in files that contain
unrelated ongoing work. Therefore, inspect the actual diff before
modifying or committing those files.

Potentially mixed files include:

app/routes/api.py
app/routes/customer.py
static/customer.js
static/styles.css
templates/customer_dashboard.html
tests/test_route_security.py
tests/test_search_service.py

Do not assume the entire contents of these files belong to Location.

Provider Search and Privacy

Provider discovery uses the customer's selected search location.

Public provider search responses must continue to respect the existing
privacy boundary.

Do not expose unnecessary sensitive/provider fields such as:

phone
whatsapp
exact latitude
exact longitude
profile_code
distance_km

Where distance information is intentionally exposed, the existing
non-precise representation such as:

distance_bucket

should be preferred over exact distance.

Bike Integration

The Bike app should reuse the existing Location architecture.

A Bike request can require two locations:

Pickup
Drop

Conceptually:

Bike customer
    |
    +---- Pickup latitude/longitude
    |
    +---- Drop latitude/longitude

The Bike implementation should build on the existing Tedile Location
contract rather than creating a second unrelated location model/API.

Before implementing Bike Location functionality, inspect:

app/services/search_service.py
app/models/booking.py
migrations/versions/d9e5f7a1b2c3_add_customer_booking_location.py
docs/LOCATION_INTEGRATION.md

Then define Bike-specific pickup/drop behavior around that existing
foundation.

Routing / Directions

Provider directions/routing is part of the wider development work but
was not cleanly included in the Location-only checkpoint because the
related files also contain unrelated functionality.

Relevant files include:

app/routes/provider.py
templates/provider_directions.html
static/provider_directions.js

Do not assume these files are entirely Location-specific.

Routing should consume coordinates supplied by the Location layer.

It should not replace or duplicate the Location data contract.

The project has used OSRM for road routing, with route requests
conceptually using:

/route/v1/{profile}/{coordinates}

and options such as:

steps=true
geometries=geojson
overview=full

Development Environment

Use Development only for feature testing unless explicitly authorized
otherwise.

Do not:

touch UAT data
touch Production data
copy Production data into Development

Location testing should use synthetic Development data.

Tests

The Location/search/security test set passed during the checkpoint:

67 passed, 14 warnings

Command:

../.venv/bin/pytest -q tests/test_route_security.py tests/test_search_service.py

Also verified:

git diff --check

Result:

passed

No UAT or Production database was accessed.

Current Working Tree

Unrelated ongoing development remains outside the Location commits.

This includes work involving areas such as:

Review
Rider
Fare
Bike Ride
Provider directions/routing
Availability
Customer JavaScript
Templates
CSS
Tests

Also intentionally excluded:

database/seed_dev.py
tedile_dev_before_provider_cleanup.sql

Do not accidentally include these in a future Location commit.

Before committing mixed files:

inspect git diff

and stage only the relevant hunks.

Avoid destructive commands such as:

git reset --hard
git clean -fd
git restore .

unless explicitly authorized.

Recommended Bike Development Sequence

Read this handoff.

Read:

docs/LOCATION_INTEGRATION.md

Inspect the existing Location model/service and migration.

Understand the customer-selected search location flow.

Define Bike pickup/drop requirements.

Reuse the existing Location contract.

Add Bike-specific logic only where required.

Add tests for pickup/drop and Location behavior.

Keep Bike implementation commits separate from unrelated
Review/Fare/Rider changes.

Do not modify the existing migration history to make integration
easier.

Architecture Goal

The target architecture is:

                 Shared Tedile Location
                         |
             +-----------+-----------+
             |                       |
       Normal Services              Bike
             |                       |
      Search / Booking        Pickup / Drop / Ride

The objective is to have one reusable Location foundation, with
normal Tedile services and Bike consuming it appropriately.

Key Rule for the Next Developer

If you need a new Location capability for Bike, first ask:

Can the existing Tedile Location contract support this?

If yes, extend/reuse the existing infrastructure.

Only introduce Bike-specific Location structures when the requirement
genuinely differs, and document why.
