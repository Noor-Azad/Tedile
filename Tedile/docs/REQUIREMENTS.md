# Tedile Requirements Status

| Requirement | Description | Status |
|---|---|---|
| BR-01 | Village Bike Ride customer entry UI | Complete |
| BR-02 | Rider registration and admin approval | Complete |
| BR-03 | Village bike ride operations | Complete |
| BR-04 | Ride Fare & Pricing | Complete |
| BR-05 | Rider Ride History | Complete |
| BR-06 | Rider Ride Cancellation | Complete |

## BR-03 scope

The first ride slice supports customer requests, approved-rider discovery and
acceptance, start/complete transitions, customer cancellation of requested
rides, customer ride history/status, and read-only admin ride visibility.
Maps, live location, matching, payments, notifications, chat, and
ratings remain future work.

## BR-04 — Ride Fare & Pricing

**Status:** Complete. The initial flat-fare implementation is available; future
pricing enhancements remain out of scope.

### Objective

Introduce a simple, understandable fare for local village rides so customers
know the expected cost, riders can see the value of an accepted ride, and
administrators have a clear pricing rule to operate and review. BR-04 does not
introduce online payment or settlement.

### Finalized fare model

- Currency: Indian Rupees (INR).
- Initial model: one configurable flat fare per ride.
- Recommended development/default value: **₹50**.
- ₹50 is a configurable business value, not a permanent hardcoded decision.
- No distance component, time component, surge pricing, or dynamic pricing is
  included.
- No cancellation fee is included.
- The server calculates and owns the authoritative fare. Any client-submitted
  fare value must be ignored or rejected.
- Monetary values must be stored and displayed to two decimal places.

### Customer behavior

- The customer sees the applicable server-calculated fare on the ride-request
  page before submitting the ride.
- The customer also sees the fare on the ride result and ride status/detail
  views.
- The customer must not submit an accepted fare value as authoritative input.
- The fare remains visible while the ride is accepted/in progress and in My
  Rides after completion.
- A completed ride displays its final fare and the pricing snapshot used.

### Rider behavior

- An approved rider may see the recorded estimated fare before accepting and
  the same fare during the ride.
- A rider cannot create, edit, waive, or otherwise change the fare.
- After completion, the rider sees the recorded final fare.

### Admin behavior

- Admin can configure the base fare through the minimal Tedile Admin pricing
  functionality. Pricing configuration changes are Admin-only and use the
  project's existing protected authorization process.
- A pricing change affects only rides created after the change. Existing rides
  retain their stored pricing snapshot.
- Admin ride visibility includes the estimated/final fare and pricing snapshot
  for operational review.

### Proposed BikeRide pricing fields

The future implementation should add fields similar to:

- `estimated_fare` — the server-calculated request-time amount.
- `final_fare` — the authoritative completed-ride amount, recorded from the
  authoritative ride fare; null until completion.
- `fare_currency` — the currency code, initially `INR`.
- `pricing_version` — identifies the pricing rule/configuration used.
- `pricing_base_fare` — the base amount snapshot used for this ride, including
  the applicable ₹50 development/default value unless configuration changes.

The base fare and pricing version are snapshots, not only references to a
mutable global setting. This prevents historical rides from changing when
future pricing configuration changes. No distance or duration fields are
required for the initial flat-fare model.

### Fare lifecycle rules

| Ride status | Fare rule |
|---|---|
| `REQUESTED` | Server calculates and stores the fare snapshot in `estimated_fare`; `final_fare` is null. |
| `ACCEPTED` | The recorded estimate remains unchanged. |
| `IN_PROGRESS` | The recorded estimate remains unchanged. |
| `COMPLETED` | Server records `final_fare` from the authoritative ride fare. |
| `CANCELLED` | The stored fare snapshot remains available for history/audit, with no cancellation fee and no payment obligation. |

BR-03 currently permits customer cancellation only while `REQUESTED`, so BR-04
does not add accepted/in-progress cancellation behavior. A cancelled ride does
not create a payment obligation.

### Security and authorization

- Fare values are calculated and persisted server-side.
- Customers may view fares only for their own rides.
- Riders may view fares only for rides they are authorized to receive or have
  accepted.
- Riders and customers cannot alter fare fields through form or request-body
  values.
- Admin pricing changes must use the existing admin authorization boundary;
  the required role is Admin only.
- Any future state-changing pricing or configuration route must use the
  existing CSRF protection.
- Existing authentication, approved-Rider checks, BikeRide ownership checks,
  and authorization rules remain in force.

### Acceptance criteria

- The server calculates the configured flat fare for a new ride request.
- A customer can view the estimate for their own ride.
- An arbitrary customer-supplied fare is ignored or rejected and cannot become
  the authoritative fare.
- An approved rider can view the fare for an eligible/assigned ride.
- A rider cannot modify the fare.
- Completion records the final fare according to the selected pricing rule.
- Cancelled rides retain any calculated fare snapshot for audit/history, do not
  receive a cancellation fee, and do not create a payment obligation.
- Completed rides retain their historical fare after later pricing changes.
- A pricing change applies only according to the approved snapshot rule for
  newly created rides.
- The existing BR-03 lifecycle and authorization behavior continue to work.
- Existing provider, Service, and normal `Booking` functionality remains
  unaffected.

### Dependencies

- BR-01 customer Bike Ride entry points.
- BR-02 Rider registration and admin approval.
- BR-03 `BikeRide` lifecycle and approved-Rider authorization.
- Existing authentication, role checks, ownership checks, and CSRF mechanism.
- Existing local SQLite/PostgreSQL configuration conventions.

### Explicit exclusions

BR-04 only calculates, displays, and stores the ride fare. It does not include
online payment, payment gateways, cash/payment collection, wallets, refunds,
rider settlement, commissions, coupons, surge or dynamic pricing, subscriptions,
live GPS tracking, maps, automated distance routing, notifications, or
ratings/reviews.

### Open Business Decisions

The core BR-04 business decisions are finalized. The following implementation
details remain future planning choices rather than blockers to implementation:

1. The exact Admin pricing-screen workflow and audit history for configuration
   changes.
2. The pricing-version format and deployment/configuration storage mechanism.

## BR-05 — Rider Ride History

**Status:** Complete. The read-only Rider Ride History implementation is
available and verified.

### Objective

Allow an approved Rider to view a read-only history of rides previously
assigned to that Rider after those rides are no longer active. Rider history
means rides handled by the Rider; it does not mean a history of every status
transition within a ride.

### Scope

Rider Ride History displays, at minimum:

- Ride date/time.
- Pickup location/address.
- Destination location/address.
- Recorded ride status.
- Recorded fare and currency.
- The ride's association with the currently authenticated Rider.

History should include rides previously assigned to the Rider, including
completed rides and cancelled rides according to their recorded ride status.
It should remain separate from the Rider's active ride list.

### Security and authorization

- Only an authenticated approved Rider may access Rider Ride History.
- The server must filter history by the Rider record associated with the
  authenticated user.
- A Rider may see only rides whose `rider_id` belongs to that Rider.
- Changing a ride ID or other URL parameter must not expose another Rider's
  ride.
- The history view is read-only, so no new state-changing operation is
  introduced and existing CSRF/security conventions remain unchanged.
- Existing authentication, approved-Rider checks, and ride ownership rules
  remain authoritative.

### Acceptance criteria

- **AC-01:** An approved Rider can access Rider Ride History.
- **AC-02:** History contains rides assigned to that Rider.
- **AC-03:** Completed rides are visible in history.
- **AC-04:** Cancelled rides associated with the Rider are handled according to
  their recorded ride status.
- **AC-05:** Fare and currency are displayed from the ride's recorded fare
  snapshot.
- **AC-06:** Historical rides remain visible after leaving Active Rides.
- **AC-07:** A Rider cannot view another Rider's rides.
- **AC-08:** URL/ID tampering cannot bypass Rider ownership.
- **AC-09:** Customer ride history remains unchanged.
- **AC-10:** Existing BR-01 through BR-04 behavior remains unaffected.
- **AC-11:** CSRF and security conventions remain unchanged; this feature is
  read-only.
- **AC-12:** Existing marketplace `Booking` functionality remains unaffected.

### Dependencies

- BR-02 Rider registration and approval.
- BR-03 `BikeRide` lifecycle and Rider ownership enforcement.
- BR-04 recorded fare and currency snapshots.
- Existing authentication and authorization mechanisms.

### Explicit exclusions

BR-05 does not include ratings/reviews, earnings or payment settlement, live
location, maps, route history, fare calculation changes, ride status-history or
audit functionality, changes to customer ride history, changes to marketplace
`Booking` functionality, or new database entities unless a later design review
determines that an existing model cannot support the requirement.

Ride status history remains a separate deferred capability. BR-05 shows the
recorded status of each historical ride only.

## BR-06 — Rider Ride Cancellation

**Status:** Complete. Rider cancellation is implemented and verified.

### Objective

Allow an approved Rider assigned to a ride to cancel that ride before the trip
starts, while preserving the existing ownership, lifecycle, fare, and customer
visibility rules.

### Scope and business rules

- An assigned Rider may cancel a ride only while its status is `ACCEPTED`.
- Cancellation is rejected for `REQUESTED`, `IN_PROGRESS`, `COMPLETED`, and
  `CANCELLED` rides.
- Only the Rider assigned to the ride may perform the cancellation.
- On success, the BikeRide status becomes `CANCELLED` and the ride becomes
  eligible for Rider Ride History.
- The existing fare snapshot is retained. No cancellation fee, payment, or
  settlement processing is introduced.
- The customer sees the ride's recorded status as `CANCELLED`.
- Existing customer cancellation rules remain unchanged.

### Security and authorization

- The Rider must be authenticated and have an approved Rider application.
- The server must scope the operation by the authenticated Rider's `rider_id`;
  changing a ride ID must not permit access to another Rider's ride.
- The state-changing operation must use the existing CSRF protection.
- Existing authentication, role, ownership, and lifecycle checks remain
  authoritative.

### Acceptance criteria

- **AC-01:** The assigned approved Rider can cancel an `ACCEPTED` ride.
- **AC-02:** Cancellation changes the ride status to `CANCELLED`.
- **AC-03:** The recorded fare snapshot remains unchanged and no cancellation
  fee or payment obligation is created.
- **AC-04:** The cancelled ride appears in the assigned Rider's history.
- **AC-05:** The customer can see the ride as `CANCELLED`.
- **AC-06:** Cancellation is rejected for `REQUESTED`, `IN_PROGRESS`,
  `COMPLETED`, and already `CANCELLED` rides.
- **AC-07:** Another Rider cannot cancel the ride, including through URL or ID
  tampering.
- **AC-08:** Unauthenticated, pending, or non-approved Riders cannot cancel.
- **AC-09:** CSRF is required for cancellation.
- **AC-10:** Existing customer cancellation and BR-02 through BR-05 behavior
  remain unaffected.
- **AC-11:** Existing marketplace `Booking` functionality remains unaffected.

### Dependencies

- BR-03 BikeRide lifecycle and Rider ownership enforcement.
- BR-04 recorded fare snapshots.
- BR-05 Rider Ride History.
- Existing authentication, authorization, and CSRF mechanisms.

### Explicit exclusions

BR-06 does not include payment, settlement, cancellation fees, cancellation
reasons, maps, routing, live location, notifications, dynamic pricing, or
unrelated UI redesign. It does not change customer cancellation behavior or
the marketplace `Booking` workflow.
