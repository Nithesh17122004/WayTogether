# Phase 7 — Financial management and sandbox-only payment simulation

## Goal
Freeze final eligible-expense shares after a journey and provide a safe test record of the passenger payment state flow. No real funds move in this phase.

## Driver finalization
A verified Driver can submit the actual eligible expense breakdown after the journey's scheduled departure time. The server locks the Journey, snapshots confirmed bookings, creates the immutable settlement and per-booking passenger contributions, and marks the journey completed.

Only confirmed seats are included. Pending, declined and cancelled bookings are excluded.

## Cost allocation
The driver is one participant. Every confirmed passenger seat is one additional participant.

`total people = 1 driver + sum(confirmed booking seats)`

`per seat amount = floor(total eligible amount in paise / total people)`

`driver share = per seat amount + any paise remainder`

`booking contribution = per seat amount × booking seat count`

This guarantees the driver share plus passenger contributions reconcile exactly to the driver-declared eligible expense total. The driver share is the driver's own cost contribution, not income or a payout.

## API
Prefix: `/api/v1/finance/`

- `POST journeys/{journey_id}/settlement/`
- `GET journeys/{journey_id}/settlement/`
- `GET contributions/mine/`
- `POST contributions/{contribution_id}/sandbox-payment/`
- `POST payments/{payment_id}/sandbox-result/`
- `POST payments/{payment_id}/sandbox-refund/` (staff administrator only)

## Sandbox states
- `created`: fake test transaction created.
- `succeeded`: simulated success.
- `failed`: simulated failure; a new test attempt may be started.
- `refunded`: full simulated refund recorded by a staff administrator.

All references are internal UUIDs. No gateway is contacted. The payment records do not represent money received or moved.

## Safety controls
- `FINANCE_SANDBOX_ENABLED` controls the fake test endpoints. It defaults to true in local DEBUG mode and false when DEBUG is false.
- `LIVE_PAYMENTS_ENABLED` is hard-coded to false.
- There is no live provider adapter or live charge endpoint.
- No bank, UPI, card or provider credentials are requested.
- No driver payout, commission or platform fee is implemented.
- Sandbox refunds do not issue money.
- Passenger contribution visibility is restricted to the owning passenger.
- Driver settlement visibility is restricted to the journey driver.
- Sandbox refunds can only be recorded by Django staff administrators.

## Not included
- Live Razorpay, Cashfree, Stripe or UPI integration.
- Live payments, capture, refunds, escrow, payouts or settlements to a driver.
- Platform commission, GST invoices or tax computations.
- Receipt upload, receipt review, dispute handling or independent expense verification.
- Payment notifications or receipts.
- Final legal classification of eligible expenses.

## Production gate
Before considering real-money functionality, separately review the private carpool operating model, eligible expense categories, insurance, state-specific requirements, tax/GST treatment, payment-provider terms and any required licences. Passing software tests does not establish legal or regulatory approval.
