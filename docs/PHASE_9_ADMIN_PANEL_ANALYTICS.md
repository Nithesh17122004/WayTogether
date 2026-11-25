# Phase 9 — Admin Panel and Platform Analytics

## Purpose
Provide authorised staff administrators with a consolidated, read-only view of WayTogether platform activity while reusing the verification and safety workflows already introduced in earlier phases.

## Frontend routes
- `/admin` — live platform overview and six-month journey activity.
- `/admin/users` — searchable account directory with role and active-state filters.
- `/admin/journeys` — journey monitoring with route/driver search, status, seats and estimates.
- `/admin/bookings` — booking oversight with participant names, status, seats and provisional contribution estimates.
- `/admin/finance` — read-only finalised expense allocation ledger.
- `/admin/verification` — existing protected driver-document review queue.
- `/admin/safety` — existing staff-only safety report queue.

## API
All endpoints below are staff-only and use Django REST Framework's `IsAdminUser` permission:
- `GET /api/v1/admin/overview/`
- `GET /api/v1/admin/users/?q=&role=&active=`
- `GET /api/v1/admin/journeys/?q=&status=`
- `GET /api/v1/admin/bookings/?q=&status=`
- `GET /api/v1/admin/expense-ledger/`

List endpoints return up to 100 newest matching records and include a total count. Search and status/role filters are optional.

## Dashboard metrics
The overview aggregates:
- Total, active and inactive accounts; role counts and email/phone verification counts.
- Driver-profile and vehicle verification status counts and current pending document count.
- Journey and booking status totals, confirmed seats and monthly journey creation over the last 180 days.
- Safety report status counts and urgent open/under-review report count.
- Finalised eligible expense totals, driver's own expense shares, passenger contribution allocations and sandbox payment attempt counts.

## Privacy and operational boundaries
- Account listing returns name, email, role, active state, verification flags and join date. It does not return phone numbers, passwords, emergency contacts or identity documents.
- Journey and booking screens are monitoring-only. They do not modify or cancel user activity.
- Verification decisions continue to use the existing protected document-review API.
- Safety-report status and private notes continue to use the existing staff-only safety API. The general dashboard does not duplicate report contents or internal notes.
- The expense ledger is a read-only cost-allocation view. Amounts represent eligible journey expenses and participant shares, not platform revenue, driver earnings, money collected, transfers or payouts.
- Sandbox payment counts describe simulated test records only.
- No real payment, payout, refund, account suspension, bulk export or destructive administrator action is introduced in this phase.

## Validation
Backend tests cover staff-only access, overview aggregation, user search/privacy and read-only ledger access. CI runs Django system checks, migration consistency checks, backend tests and frontend TypeScript/production build.
