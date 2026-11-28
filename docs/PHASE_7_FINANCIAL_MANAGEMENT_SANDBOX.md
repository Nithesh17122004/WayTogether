# Phase 7 — Expense sharing and Razorpay Test Mode

## Expense finalization
A verified Driver can submit actual eligible expenses after the journey's scheduled departure. The backend freezes confirmed bookings, calculates the driver's and passengers' equal expense shares, creates contribution records and marks the journey completed.

The driver is one cost-sharing participant. Integer paise arithmetic ensures the allocated shares reconcile to the eligible-expense total. No driver earnings, platform commission or payout is created.

## Razorpay Test Mode integration
WayTogether uses Razorpay Standard Web Checkout in **Test Mode only**.

1. The backend creates a Razorpay Order using the server-calculated passenger contribution.
2. The frontend opens Razorpay Checkout using the public Test Mode key ID and the server-created order ID.
3. After Checkout returns, the backend verifies the HMAC-SHA256 signature using the order ID saved on the server and the secret held only in the backend environment.
4. The backend fetches the payment from Razorpay, checks the order ID, amount and currency, captures an authorised payment when required, and marks the contribution paid only after Razorpay reports `captured`.
5. Failed test attempts can be retried with a new order.

API prefix: `/api/v1/finance/`

- `POST journeys/{journey_id}/settlement/`
- `GET journeys/{journey_id}/settlement/`
- `GET contributions/mine/`
- `POST contributions/{contribution_id}/razorpay-order/`
- `POST payments/{payment_id}/razorpay-verify/`
- `POST payments/{payment_id}/razorpay-failed/`

## Required environment variables
- `RAZORPAY_TEST_MODE=true`
- `RAZORPAY_KEY_ID=rzp_test_...`
- `RAZORPAY_KEY_SECRET=...`

The backend rejects a non-test key ID. Store the secret only as a private Render environment variable. Never commit the secret to Git or expose it to the frontend.

## Test transactions
Razorpay Test Mode simulates Checkout and does not deduct real money. Use the payment methods and test credentials supplied in Razorpay's Test Mode documentation.

## Not included
- Live Razorpay keys or live payments.
- Platform commission, GST invoices or tax calculations.
- Driver payouts, escrow, split settlements or bank transfers.
- Production webhooks, automated dispute handling or receipt reconciliation.
- Refund processing.

## Go-live gate
A separate reviewed change is required before live keys can be enabled. It must include provider dashboard configuration, signed webhooks, capture/settlement reconciliation, refund support, legal and regulatory review of the private carpool expense-sharing model, insurance review, tax/GST treatment and provider approval. Do not switch `RAZORPAY_TEST_MODE` off as a shortcut.
