# WayTogether

**Share the same route.**

WayTogether is a website-first private carpooling platform designed to connect people travelling along the same route. Its operating model is based on independently planned journeys and reasonable sharing of eligible journey expenses.

> Real-money operations must remain disabled until the applicable legal, tax, insurance and payment-provider reviews are complete.

## Product direction

- Responsive website first; Pan-India technical architecture.
- Premium mobility-tech brand identity.
- Genuine pre-planned private carpool journeys.
- No taxi-style commercial trip creation or driver-profit model.
- Clearly distinguish the driver's eligible expense contribution from any separately disclosed and legally approved platform fee.

## Technology

- Frontend: React, Vite, TypeScript and Tailwind CSS.
- Backend: Python, Django and Django REST Framework.
- Database: PostgreSQL in shared/production environments; SQLite for local backend development.
- Maps: Leaflet, configurable OpenStreetMap-derived tiles, location search and a configurable road-routing provider.
- Testing: Pytest and Playwright; GitHub Actions CI is configured.

## Repository layout

```
frontend/   React website and UI prototype
backend/    Django REST API foundation
docs/       Product requirements, architecture, roadmap and brand guidance
.github/    Continuous integration
```

## Run locally

### Frontend

Requirements: Node.js 20.19+ or 22.12+ and npm.

```bash
cd frontend
npm install
npm run dev
```

### Backend

Requirements: Python 3.11+.

```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

Health endpoint: http://127.0.0.1:8000/api/v1/health/

The website now supports API-backed driver KYC, vehicle verification, journey publishing/search, passenger booking requests, driver approvals and seat availability/cancellation management. Final eligible-expense settlements and fake sandbox payment/refund simulation are implemented in Phase 7. Live payments, driver payouts, messaging and live tracking are not implemented.

## Development phases

1. Repository and architecture foundation
2. Premium UI/UX and frontend
3. Authentication and user management
4. Driver, vehicle and document verification
5. Journey publishing and search — implemented in Phase 5
6. Booking and journey management — implemented in Phase 6
7. Payments and financial management — expense settlement and sandbox simulation implemented; live payments remain disabled
8. Communication, safety and trust
9. Admin panel and analytics
10. Testing, security and deployment

See the `docs/` directory for full product requirements, architecture, roadmap and brand guidance.

## Core product safeguards

- Drivers must independently plan journeys and attest that they would travel without passengers.
- Passenger contributions are estimates of eligible journey expenses, not fares or driver income; provisional shares are recalculated as confirmed seat occupancy changes. Final payment allocation is still pending.
- Passenger contributions are intended for eligible journey-expense sharing, not driver profit.
- Platform fees must be separately disclosed and used only after legal and tax review.
- Live payments and payouts must not be enabled until the operating model, insurance, tax position and payment provider are approved.
- Pan-India technical support does not itself establish permission to operate in every state.
