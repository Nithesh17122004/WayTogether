# Phase 5 — Journey publishing, search and maps

## Objective
Implement the first API-backed carpool marketplace flow for journeys that drivers independently planned and would make even if no passenger joined. Passenger contributions are represented as estimates of eligible shared journey expenses, not commercial fares.

## Journey data
A journey stores:
- Owner Driver and selected approved Vehicle.
- Origin/destination display names and coordinates.
- Travel date, departure time and passenger seats offered.
- Ordered intermediate stops (up to four).
- Estimated fuel, toll, parking and other eligible expense categories.
- Optional route distance, duration and GeoJSON coordinate geometry.
- Independent-planning and expense-only attestations.
- Status: draft, published, cancelled or completed.

## Driver journey flow
1. Driver must have an active account with email and mobile verified.
2. Driver selects a vehicle registered to their account.
3. Driver selects origin and destination by explicit location search.
4. Driver may add up to four ordered intermediate stops.
5. Driver enters the date, time, seats and eligible expense estimate.
6. Driver confirms that the trip was independently planned and is not being created to earn passenger-transport income.
7. The API creates a private Draft.
8. Publish checks the driver's current verification status, the vehicle's current verification status, future departure time and the expense-sharing attestations.
9. Approved journeys appear in public search and detail pages.

A driver can save a draft before KYC/vehicle approval, but cannot publish it until both are approved.

## Expense-sharing estimate
The backend adds fuel, toll, parking and other estimated eligible expenses. It calculates a per-passenger estimate as:

`estimated_total_expenses / (seats_offered + 1 driver)`

This is a preview that assumes every offered passenger seat is occupied. Phase 6 must calculate the final contribution against actual confirmed passengers and any approved cost allocation policy. There is no commission, driver profit, reservation or payment in Phase 5.

## Search matching
- Passenger search supplies coordinates for pickup and drop-off, a date, seat count and radius.
- API only searches published journeys with an active, contact-verified driver whose driver verification remains approved and whose selected vehicle remains approved.
- Search considers ordered waypoints: journey origin, intermediate stops and journey destination.
- A valid match requires a pickup waypoint and a later drop-off waypoint both within the requested radius.
- Results are ordered by combined pickup/drop-off distance.
- Same-day departures that have already passed are excluded.
- Initial implementation scans at most 1,000 journeys for the requested date using application-side Haversine distance. This is an MVP implementation; before Pan-India scale, move the search to PostGIS/spatial indexes, add pagination and performance tests.

## API endpoints

Prefix: `/api/v1/journeys/`

- `GET locations/search/?q=...`
- `GET route-preview/?origin_lat=...&origin_lon=...&destination_lat=...&destination_lon=...`
- `GET /` — public search with coordinate/date/seat/radius query parameters
- `POST /` — create a draft (verified Driver)
- `GET mine/` — list the current driver's journeys
- `GET {id}/` — published journey or owner's own draft
- `PATCH {id}/edit/` — edit a draft
- `POST {id}/publish/` — publish a draft after server-side eligibility checks
- `POST {id}/cancel/` — cancel own draft/published journey

## Map provider decisions
- Location search is explicit button-triggered search; it must not be changed to keystroke autocomplete on public Nominatim.
- Geocoding results are cached and the application enforces one uncached Nominatim request per second. Production must use shared cache/rate coordination across instances.
- Road routing is provider-configurable and disabled by default. Configure a routing endpoint only after confirming its license/terms, usage limit and SLA fit the deployment.
- Development map tiles can use the standard OpenStreetMap tiles with visible attribution. Production must configure a provider that permits the planned commercial use or self-host tiles.
- No bulk/offline tile downloads are supported.

## Not in Phase 5
- Passenger booking and atomic seat reservation.
- Seat count reduction from confirmed bookings.
- Final cost-sharing allocation.
- Payment collection, commission, refunds or driver payouts.
- Passenger/driver chat and notifications.
- Live location sharing.
- Rating and review workflow.
