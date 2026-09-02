# Tedile Location Integration

## Purpose

Tedile lets a customer choose a search location, discover nearby providers, and optionally save a service location on a booking. The saved booking location is available to the authorized provider for in-app directions.

## Current architecture

The customer UI in `static/customer.js` maintains separate concepts:

- `state.searchLocation` and `state.searchLocationLabel`: used only for provider discovery.
- `state.bookingLocation` and `state.bookingLocationLabel`: used only when creating a booking.

Manual location search calls `GET /api/search/geocode?q=...`, stores the returned locality in `searchLocation`, and sends its coordinates to `GET /api/search/providers`.

“Use my current location” uses the browser Geolocation API after the customer clicks the control. It sets both search and booking locations to the GPS coordinates. On a provider profile, the customer can explicitly choose either current GPS location or the selected search location for the booking.

The booking form posts the selected booking coordinates to `POST /customer/bookings`. The backend validates the pair and stores it on `Booking`. Provider search does not expose exact provider coordinates in its public DTO.

## Data/API contract

Existing customer booking fields:

```text
customer_latitude
customer_longitude
customer_location_label
```

`customer_latitude` and `customer_longitude` must be supplied together and must be within latitude `-90..90` and longitude `-180..180`. The label is optional and is limited to 160 characters.

`GET /api/search/geocode?q=<location>` returns seeded locality data, including the locality coordinates used by the customer search UI.

`GET /api/search/providers` accepts `latitude`, `longitude`, `radius`, `service`, `keyword`, sorting, and pagination parameters. Exact distances are kept out of the public response; providers receive a coarse `distance_bucket`.

An authorized provider may use `POST /provider/bookings/<booking_reference>/directions`. The protected response includes provider and booking customer coordinates for that provider-owned booking, plus route data when routing is available. These coordinates are not part of the normal provider booking DTO.

## Customer service integration

Service discovery should pass the selected search coordinates to `/api/search/providers`. The service filter can be sent as the existing `service` slug, for example `ac-repair`.

The configured search radius defaults to 50 km and uses progressive bands `[5, 10, 25, 50]`. This controls discovery only. It does not restrict directions for an existing booking.

## Bike service integration

No Bike-specific location API currently exists. The Bike service should reuse the existing `Booking` location fields and customer location state rather than create a second location model.

**Recommendation:** Bike booking creation should submit the existing `customer_latitude`, `customer_longitude`, and `customer_location_label` fields to `POST /customer/bookings` when the Bike workflow represents a service location. Any new Bike endpoint should document whether it consumes the same fields, but that endpoint is not implemented by the current Location feature.

## Coordinates

Coordinates are decimal latitude/longitude values. Search coordinates are sent as query parameters to provider search. Booking coordinates are submitted in the authenticated customer booking POST and stored on the booking. Provider directions uses the provider’s browser coordinates when supplied, otherwise the provider’s stored profile coordinates, and uses the booking’s customer coordinates as the destination.

Exact customer coordinates are not included in public provider DTOs or ordinary provider dashboard booking DTOs.

## Existing examples

Geocode example:

```text
GET /api/search/geocode?q=Kolkata
```

Provider search example:

```text
GET /api/search/providers?latitude=22.5726&longitude=88.3639&service=ac-repair
```

Booking form fields sent to the existing route:

```text
POST /customer/bookings
provider_profile_code=<provider profile code>
service_slug=ac-repair
customer_latitude=<selected booking latitude>
customer_longitude=<selected booking longitude>
customer_location_label=Your current location
```

The response is the existing customer booking DTO and does not expose customer coordinates.

## Files involved

- `app/models/booking.py` — booking location columns and provider/customer DTO behavior.
- `app/routes/customer.py` — authenticated booking creation and coordinate validation.
- `app/routes/api.py` — geocoding and provider search routes.
- `app/routes/provider.py` — authorized provider directions route.
- `app/services/geo_service.py` — locality lookup and distance calculation.
- `app/services/search_service.py` — provider filtering, radius bands, and distance buckets.
- `static/customer.js` — search/booking location state and browser geolocation.
- `static/provider_directions.js` — provider directions display.
- `templates/customer_dashboard.html` — customer search controls.
- `templates/provider_profile.html` — provider profile shell hosting the booking flow.
- `templates/provider_directions.html` — provider directions view.
- `static/styles.css` — existing Location/directions presentation.

## Database and migrations

The Location-specific schema migration is:

```text
migrations/versions/d9e5f7a1b2c3_add_customer_booking_location.py
```

It adds the three nullable customer booking location columns to `bookings`. Its migration dependencies must remain intact when integrating the branch. Review, rider, and fare migrations are not Location feature files.

## Testing

Location/search behavior is covered by tests in `tests/test_route_security.py` and `tests/test_search_service.py`, including coordinate validation, booking persistence, public DTO privacy, progressive-radius search, availability handling, and synthetic provider discovery.

Relevant command:

```bash
../.venv/bin/pytest -q tests/test_route_security.py tests/test_search_service.py
```

Frontend syntax checks:

```bash
node --check static/customer.js
node --check static/provider_directions.js
```

## Bike integration notes

Use the existing customer location controls and booking fields. Treat search location and booking/service location as separate values: a manual search locality must not silently become the booking location. If Bike needs a customer service location, require an explicit booking-location choice and submit the existing three booking fields. Do not add a competing Bike-specific coordinate model unless a future design explicitly requires it.
