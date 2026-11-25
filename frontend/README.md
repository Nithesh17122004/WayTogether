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
- `/publish` — Driver journey draft form
- `/login` — API-connected sign-in
- `/register` — API-connected registration and email/mobile verification
- `/dashboard/passenger` — Passenger dashboard preview
- `/dashboard/driver` — Driver dashboard preview
- `/admin` — Admin dashboard preview

## Authentication notes
- Registration and login call the Django authentication endpoints.
- Email and phone codes must both be verified before login.
- In local development, email OTP is printed by Django's console email backend and phone OTP is logged in the Django server console.
- Production SMS delivery requires a provider integration before phone verification can be used.
- JWTs are held in memory in this initial browser client. Refreshing the page clears the session and the user must sign in again. A production-grade secure cookie/token strategy and protected dashboard routes remain required before launch.

Journey cards, user profiles and dashboard metrics remain illustrative. Search is not connected to a live journey API. Journey publication, bookings, documents, messaging, admin actions and payments are not connected in this phase. No payments or payouts occur.
