# WayTogether Website

## Requirements
- Node.js 20.19+ or 22.12+
- npm

## Setup
```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

Set `VITE_API_BASE_URL` to the Django API base path. By default, the frontend calls `http://127.0.0.1:8000/api/v1`.

## Available routes
- `/` — Public homepage
- `/search` — Live journey search by origin, destination, date, seats and radius
- `/journeys/:id` — Published journey details, route and intermediate stops
- `/publish` — Driver journey draft creation and publication
- `/login` — API-connected sign-in
- `/register` — API-connected registration and email/mobile verification
- `/dashboard/passenger` — Passenger dashboard (booking data comes in Phase 6)
- `/dashboard/driver` — Driver dashboard overview
- `/dashboard/driver/journeys` — API-backed driver drafts and published journeys
- `/driver/verification` — Driver profile, vehicle registration, document upload and submission
- `/admin` — Admin dashboard overview
- `/admin/verification` — Staff-only document review queue

## Journey search and publishing (Phase 5)
- Search locations by entering a full city, town or landmark and pressing **Find**. The location picker intentionally does not call the public geocoder on every keystroke.
- Select the origin and destination from search results.
- Search matches both endpoints against an ordered journey path, including saved intermediate stops.
- Drivers can save a journey as a draft and publish only after driver and vehicle verification is approved.
- Expense entries are estimates for fuel, tolls, parking and other eligible shared costs. The displayed per-passenger estimate assumes every offered passenger seat is occupied, including the driver in the split.
- A final passenger cost allocation, seat reservation, payment or payout is not implemented until Phase 6/7.

## Map configuration
- During local development, the Leaflet map uses the standard OpenStreetMap raster tiles by default.
- Before production, configure `VITE_OSM_TILE_URL` and `VITE_OSM_TILE_ATTRIBUTION` to a tile provider whose terms explicitly permit your commercial use, or self-host tiles.
- Keep provider attribution visible and honour caching. Do not use bulk/offline tile downloads.
- The road-route line, distance and duration are optional. Configure `OSRM_ROUTE_URL` on the backend with a provider permitted for your deployment. It is deliberately blank by default.
- Location lookup is user-triggered, cached and globally limited to one uncached request per second. Before scaling the backend to multiple instances, use a shared cache (for example Redis) to enforce that limit across instances.

## Authentication
- Registration and login call Django authentication endpoints.
- Email and phone codes must both be verified before login.
- In local development, email OTP is printed by Django's console email backend and phone OTP is logged in the Django server console.
- Production SMS delivery requires a provider integration.
- JWTs are currently kept in memory; refreshing the page clears the session. A production-grade secure browser/session strategy and protected route enforcement remain launch prerequisites.

## Driver verification
- Driver verification pages require a verified Driver account.
- Documents are uploaded as multipart form data and private downloads use the authenticated API.
- PDF, JPG/JPEG and PNG uploads up to 8 MB are accepted.
- Admin verification requires a Django staff account.
- Use persistent private file storage in production. Do not expose the Django media directory through a public URL.

Bookings, seat locking, payments, refunds, payouts, messaging and live tracking are not active in this phase.


## Booking and seat management (Phase 6)
- Passenger journey pages allow requests for one or more available seats.
- Pending requests are sent to the driver and do not hold seats.
- Drivers review requests in `/dashboard/driver/bookings`, then approve or decline.
- Approving a request reserves its seats, with the server checking capacity inside a database transaction.
- Passenger booking history is available at `/dashboard/passenger/bookings`.
- Passengers can cancel their own pending/confirmed bookings before departure.
- Driver cancellation of a journey closes its pending and confirmed bookings.
- Search and journey details show confirmed and available seat counts.
- Provisional expense shares are recalculated after confirmations/cancellations; they are not final prices and no money is collected.
