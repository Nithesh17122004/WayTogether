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
- `/search` — Journey search and sample result cards
- `/journeys/:id` — Journey details preview
- `/publish` — Journey draft form
- `/login` — API-connected sign-in
- `/register` — API-connected registration and email/mobile verification
- `/dashboard/passenger` — Passenger dashboard preview
- `/dashboard/driver` — Driver dashboard overview
- `/driver/verification` — Driver profile, vehicle registration, document upload and submission
- `/admin` — Admin dashboard preview
- `/admin/verification` — Staff-only document review queue

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

Journey search, publishing, bookings, messaging and payment flows remain unconnected. Driver/vehicle records and documents are API-backed in this phase; journeys are still illustrative.
