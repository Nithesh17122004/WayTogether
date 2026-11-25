# WayTogether Technical Architecture

## Architecture style
Start as a modular monolith. Separate frontend and backend applications, but keep backend business domains in one Django deployment until scale justifies otherwise.

## Stack
- Frontend: React, Vite, TypeScript, Tailwind CSS.
- Backend: Python, Django, Django REST Framework.
- Database: PostgreSQL.
- Maps: Leaflet and OpenStreetMap.
- Background tasks: Celery and Redis when asynchronous tasks are introduced.
- Realtime: Django Channels when messaging is implemented.
- Tests: Pytest and Playwright.
- Hosting target: Vercel (frontend) and a suitable managed Python/PostgreSQL host (backend/database).

## Repository layout
- frontend/: public website and authenticated dashboards.
- backend/: Django project and domain apps.
- docs/: product, architecture and operational documentation.

## Backend domains
accounts, profiles, drivers, vehicles, verifications, journeys, bookings, communications, notifications, reviews, safety, support, payments, analytics.

## Data ownership
Django/PostgreSQL is authoritative for users, verification, journeys, seat inventory, bookings and ledger records. The browser must never be trusted for authorization, seat availability, expense eligibility or payment state.

## API conventions
- Prefix APIs with /api/v1/.
- Use JSON responses and consistent validation errors.
- Enforce authorization at the view/service layer.
- Use transactions and row-level locking for booking allocation.
- Make state transitions explicit and auditable.
- Use idempotency keys for payment and booking operations where relevant.

## Security
Secrets live in environment variables, not source control. Keep document uploads private. Verify payment-provider webhooks server-side. Use HTTPS, restrictive CORS, secure cookies/session handling, rate limiting and structured audit logs.

## Deployment
Keep separate development and production settings. Use managed PostgreSQL, automated migrations, health checks, backups, error monitoring and a rollback plan. Payment production credentials must not be configured until legal/provider approval.
