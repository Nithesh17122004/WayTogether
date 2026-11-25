# Phase 6 — Booking and seat management

## Objective
Allow a verified Passenger to request one or more seats on a published journey, allow the owning Driver to approve or decline, and prevent confirmed passenger seats from exceeding journey capacity.

## Booking states
- Pending: submitted by a passenger; does not reserve seats.
- Confirmed: approved by the owning Driver; seats are reserved.
- Declined: declined by the Driver.
- Cancelled: cancelled by a participant or as part of journey cancellation.

A conditional unique database constraint permits only one pending/confirmed booking per passenger per journey.

## Passenger flow
1. Open a published journey.
2. Select the number of currently available seats.
3. Optionally add a short message.
4. Submit a request.
5. View status under `/dashboard/passenger/bookings`.
6. Cancel a pending/confirmed request before journey departure.

## Driver flow
1. Open `/dashboard/driver/bookings`.
2. Review passenger name, seats requested, date and message.
3. Optionally write a response.
4. Approve to reserve seats or decline.
5. View confirmed, declined and cancelled request history.

Only the Driver who owns the journey may approve or decline its bookings.

## Seat locking and concurrency
- Pending requests do not reduce seat availability.
- Confirming a request acquires a database transaction and row lock on the parent Journey.
- Available seats are recalculated from the sum of confirmed booking seats while the Journey lock is held.
- If the requested seats no longer fit, approval returns `409 Conflict`.
- Passenger cancellation and driver journey cancellation lock the Journey before changing booking states.
- Journey cancellation closes all pending and confirmed bookings in the same transaction.
- A conditional unique constraint prevents duplicate active bookings for one passenger/journey.

PostgreSQL row-level locking is required for production concurrency guarantees. SQLite local development tests validate functional rules but not production-grade parallel lock behavior.

## Expense contribution estimates
After each approval or confirmed-booking cancellation, estimates are recalculated using:

`estimated per-person share = eligible journey expense total / (1 + confirmed passenger seats)`

The driver counts as one participant. A booking for multiple seats receives the per-person estimate multiplied by its seat count. These estimates can change when occupancy changes. They are not payment amounts or a promise of a fixed price. The final charge point, rounding and allocation policy must be approved and implemented in Phase 7 before money is collected.

## API
Prefix: `/api/v1/bookings/`

- `POST /`
- `GET mine/`
- `GET driver/requests/`
- `GET {id}/`
- `POST {id}/approve/`
- `POST {id}/decline/`
- `POST {id}/cancel/`

Journey search and details now also return `confirmed_seats` and `available_seats`.

## Not included in Phase 6
- Payments, refunds, settlements, commission or driver payouts.
- Booking notifications, email/SMS or push.
- In-app chat or private contact detail exchange.
- Driver arrival, passenger check-in, live tracking or completion.
- Automated timeout/release of pending requests.
