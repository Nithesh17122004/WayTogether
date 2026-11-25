# WayTogether API

## Requirements
- Python 3.11 or newer
- PostgreSQL for shared development/production; SQLite is used by default locally.

## Setup
```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Health check: http://127.0.0.1:8000/api/v1/health/

## Authentication API (Phase 3)

All endpoints are prefixed with `/api/v1/auth/`.

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `register/` | Create Passenger or Driver account |
| POST | `verification/request/` | Request email or phone OTP |
| POST | `verification/confirm/` | Confirm a six-digit OTP |
| POST | `login/` | Obtain JWT access and refresh tokens |
| POST | `token/refresh/` | Refresh an access token |
| GET | `me/` | Read the authenticated profile |

## Driver and vehicle verification API (Phase 4)

All endpoints are prefixed with `/api/v1/drivers/`. Driver endpoints require a signed-in, active Driver account with both email and mobile verified. Administrator endpoints require Django staff access.

| Method | Endpoint | Purpose |
|---|---|---|
| GET / PATCH | `profile/` | Read or update the current driver's profile |
| GET / POST | `vehicles/` | List or register the current driver's vehicles |
| GET | `vehicles/{id}/` | Read an owned vehicle |
| GET / POST | `documents/` | List or upload private verification documents |
| GET | `documents/{id}/download/` | Download a document after ownership/staff permission check |
| POST | `verification/submit/` | Submit one owned vehicle and driver documents for review |
| GET | `admin/verification/queue/` | Staff-only pending document queue |
| POST | `admin/verification/documents/{id}/review/` | Staff-only approve/reject decision |

### Vehicle registration payload
```json
{
  "registration_number": "TN01AB1234",
  "make": "Honda",
  "model": "City",
  "manufacture_year": 2022,
  "colour": "Blue",
  "vehicle_type": "sedan",
  "passenger_seats": 3,
  "private_use_attested": true
}
```

A vehicle cannot be registered through this workflow unless the driver confirms it is privately used and is not being registered as a commercial taxi.

### Document upload
Send a multipart form request to `/documents/`:
- `document_type`: `driver_license`, `vehicle_registration`, `insurance`, `pollution_certificate` or `vehicle_photo`.
- `vehicle`: required for all vehicle document types and must belong to the authenticated driver. Omit for `driver_license`.
- `file`: PDF, JPG, JPEG or PNG, up to 8 MB.
- `expiry_date`: optional date in ISO format where applicable.

Driving licence, vehicle registration certificate, insurance certificate and vehicle photograph are required before a vehicle can be submitted. Pollution certificate is supported as an additional document where applicable.

### Submit a vehicle
```json
{ "vehicle_id": 12 }
```

### Administrator review
```json
{ "decision": "rejected", "review_note": "Please upload a clearer copy." }
```
Use `decision: "approved"` to approve a document. A rejection reason is mandatory. Once required documents have been individually approved, the vehicle and driver verification statuses are recalculated.

## Private document storage and production notes
- Files are stored under the private `MEDIA_ROOT/private/driver-verification/` path in local development.
- The API never returns a public media URL. Downloads go through the authenticated endpoint; owners and Django staff can download, other users receive 404.
- Do not map `MEDIA_ROOT` or `MEDIA_URL` to a public web server route.
- Before production, configure persistent private object storage (for example, a private S3-compatible bucket) or a private persistent volume and test access controls, backup, retention and deletion.
- Configure malware scanning and operational review procedures before accepting real identity/vehicle documents in production.
- Review document retention, privacy notices and access logging with the company's legal/privacy advisers.

## Local OTP delivery
- Email OTPs are printed by Django's console email backend while `DJANGO_DEBUG=true`.
- Phone OTPs are logged by Django only when `SMS_OTP_CONSOLE=true` and `DJANGO_DEBUG=true`.
- Never expose OTP values in API responses.
- Production phone verification requires an approved SMS provider.

## Security notes
- Use a unique, high-entropy `DJANGO_SECRET_KEY` in production.
- Configure `DATABASE_URL`, allowed hosts, HTTPS, CORS and SMTP through deployment secrets.
- JWT access tokens expire after ten minutes; refresh tokens expire after seven days.
- The website currently keeps JWTs in memory. A production-grade browser token/session strategy and route guards remain required before launch.


## Journey publishing and search API (Phase 5)

All endpoints are prefixed with `/api/v1/journeys/`.

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| GET | `locations/search/?q=...` | Public, throttled | Explicit user-triggered search for an Indian location |
| GET | `route-preview/?origin_lat=...&origin_lon=...&destination_lat=...&destination_lon=...` | Verified Driver | Road distance/duration/geometry from configured routing provider |
| GET / POST | `/` | Public search / verified Driver create | Search published journeys or create a private draft |
| GET | `mine/` | Verified Driver | List the current driver's own drafts and journeys |
| GET | `{id}/` | Public published journey / owner draft | Read journey details |
| PATCH | `{id}/edit/` | Owner Driver | Edit a draft |
| POST | `{id}/publish/` | Owner verified Driver | Publish after driver and vehicle approval |
| POST | `{id}/cancel/` | Owner verified Driver | Cancel a draft or published journey |

### Create a draft

A Driver account must have verified email and mobile number. The selected vehicle must belong to that driver. Vehicle approval is required before the draft can be published.

```json
{
  "vehicle": 12,
  "origin_name": "Chennai, Tamil Nadu",
  "origin_latitude": 13.0827,
  "origin_longitude": 80.2707,
  "destination_name": "Bengaluru, Karnataka",
  "destination_latitude": 12.9716,
  "destination_longitude": 77.5946,
  "travel_date": "2026-12-12",
  "departure_time": "07:30",
  "seats_offered": 2,
  "fuel_expense": "1200.00",
  "toll_expense": "250.00",
  "parking_expense": "0.00",
  "other_expense": "50.00",
  "expense_note": "Estimated fuel and toll costs",
  "description": "A journey I was already planning to make.",
  "stops": [
    {
      "location_name": "Vellore, Tamil Nadu",
      "latitude": 12.9165,
      "longitude": 79.1325
    }
  ],
  "independently_planned": true,
  "expenses_only": true
}
```

The actual response also contains a calculated `estimated_total_expenses` and `estimated_contribution_per_passenger`. The estimate divides the total expenses by the driver plus all offered passenger seats, assuming all offered passenger seats are occupied. Phase 6 must recalculate the final share from the actual confirmed passenger count. This is an expense-sharing estimate, not a passenger fare. No commission, payment or payout is implemented in Phase 5.

### Publish checks
- Driver account is active and email/mobile verified.
- Driver profile is approved.
- Selected vehicle is approved and current required documents remain valid.
- Driver attests the trip was independently planned and would take place without passengers.
- Driver confirms contributions are limited to eligible shared journey expenses.
- Estimated total expenses must be greater than zero.
- Departure date/time must still be in the future.

### Search

`GET /` accepts:
- `origin_lat`, `origin_lon`
- `destination_lat`, `destination_lon`
- `date` in ISO format (`YYYY-MM-DD`)
- `seats` (1–8)
- optional `radius_km` (1–100; default 25)

Search matches an ordered segment from the journey origin through its intermediate stops to the destination. Both passenger pickup and drop-off must be within the requested radius of an ordered pair of journey waypoints. Results are sorted by combined pickup/drop-off proximity. Only published journeys with currently approved driver and vehicle statuses appear.

The initial implementation examines up to 1,000 published journeys for the selected date and calculates geographic proximity in application code. A production Pan-India marketplace should move this to PostGIS/spatial indexes, add pagination and benchmark high-volume routes before launch.

## Map and routing provider configuration

### Location search
- Set `NOMINATIM_URL` and `MAPS_USER_AGENT` in the backend environment.
- Location results are requested only after the user presses the Find button; this UI intentionally does not provide autocomplete.
- Results are cached for 24 hours.
- The public Nominatim endpoint is guarded at one uncached request per second for the application.
- The default in-process cache is suitable only for a single development instance. Configure a shared cache such as Redis before horizontally scaling, so the global rate limit works across instances.
- Publish a monitored contact URL/email in `MAPS_USER_AGENT` before production.

### Road routing
- `OSRM_ROUTE_URL` is blank by default. Configure a routing service whose terms permit your planned use.
- Do not assume the public OSRM demo server is production infrastructure. The demo server is best-effort and its usage policy restricts traffic; it does not provide an SLA.
- A journey can still be saved without a road geometry/distance preview. The route preview is not required for draft creation or route search.

### Map tiles
- Local development can use the standard OpenStreetMap raster tiles.
- For production, configure `VITE_OSM_TILE_URL` and `VITE_OSM_TILE_ATTRIBUTION` to use a tile provider whose terms permit your commercial deployment, or self-host a tile service.
- Keep attribution visible, honour caching, and do not bulk-download tiles.
- Map tile selection is a frontend build-time environment setting.

## Phase 5 scope limitations
- Seat availability is the number of seats offered. Actual reserved/available seats will be controlled by booking transactions in Phase 6.
- No reservation, payment, payout, commission, chat, live tracking or passenger contact disclosure is enabled.
- Stop matching supports only the ordered saved waypoints, not arbitrary pickup/drop-off points along a road polyline.
- Road distance and estimated duration are only present when a routing provider is configured.


## Booking and seat management API (Phase 6)

All endpoints are prefixed with `/api/v1/bookings/`.

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| POST | `/` | Verified Passenger | Request seats on a published journey |
| GET | `mine/` | Verified Passenger | List the passenger's own bookings |
| GET | `driver/requests/` | Verified Driver | List requests for the driver's journeys; optional `?status=pending` |
| GET | `{id}/` | Booking passenger or journey driver | Read one booking |
| POST | `{id}/approve/` | Owning verified Driver | Approve a pending request and reserve seats |
| POST | `{id}/decline/` | Owning verified Driver | Decline a pending request |
| POST | `{id}/cancel/` | Booking passenger or journey driver | Cancel a pending/confirmed booking before departure |

### Create a passenger booking request

```json
{
  "journey": 42,
  "seats_requested": 1,
  "request_message": "I can meet at the agreed pickup point."
}
```

A request starts as `pending`. Creating a pending request does not reserve seats. The driver must approve it before the seats are counted as confirmed. One passenger may have only one pending or confirmed booking for the same journey.

### Driver approval

```json
{
  "driver_response": "Confirmed. See you at the pickup point."
}
```

Approval runs inside a database transaction and locks the Journey row before checking the confirmed seat count. If enough seats no longer remain, the API returns `409 Conflict` and does not confirm the request. The approval also checks that the journey is still published, has not departed, and the driver profile and selected vehicle remain approved.

### Booking statuses
- `pending`: sent to the driver; does not reserve seats.
- `confirmed`: driver approved; requested seats are reserved.
- `declined`: driver declined the request.
- `cancelled`: passenger, driver or journey cancellation closed the booking.

The database enforces a conditional unique constraint so a passenger cannot have more than one active (pending/confirmed) booking for a journey. Once a booking is declined or cancelled, the passenger may submit a new request while the journey is still eligible and has availability.

### Cancellation
- A passenger may cancel their own pending or confirmed booking before departure.
- A driver may cancel a booking before departure.
- Cancelling a journey also cancels all its pending and confirmed bookings in the same transaction.
- After departure, normal booking cancellation is blocked.
- Cancelled confirmed bookings release their seats.

### Seat and expense allocation rules
- `seats_offered` is the maximum number of passenger seats on the journey.
- `confirmed_seats` is the sum of seats on confirmed bookings only.
- `available_seats = seats_offered - confirmed_seats`.
- Pending requests do not count as reserved seats.
- Search checks `available_seats`, not just the originally offered seat count.
- After a booking is approved or a confirmed booking is cancelled, provisional eligible-expense estimates are recalculated equally across the driver plus all currently confirmed passenger seats. A multi-seat booking receives that per-person estimate multiplied by its seat count.

These amounts are estimates only. They can change as more seats are confirmed or cancelled. No money is collected, charged, refunded or paid out in Phase 6. Phase 7 must define the final amount calculation and freeze point before payments are enabled.

### Concurrency and production database
The approve/cancel journey workflows use `transaction.atomic()` and `select_for_update()` on the parent Journey row so competing approvals are serialized on databases that support row-level locks (such as PostgreSQL). The conditional unique constraint also protects duplicate active requests. SQLite local development does not provide equivalent row-locking behavior; concurrency testing must be repeated against PostgreSQL before production.

## Phase 6 scope limitations
- No payment collection, refunds, driver payouts or commission.
- No chat, email/SMS booking notifications or push notifications; these belong to Phase 8.
- No in-app contact detail exchange.
- No check-in/live journey tracking or completion workflow.
- No automatic release/expiry of pending requests before departure.
