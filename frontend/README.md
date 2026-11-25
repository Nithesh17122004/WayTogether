# WayTogether Website

## Requirements
- Node.js 20.19+ or 22.12+
- npm

## Setup
```bash
cd frontend
npm install
npm run dev
```

Production build:
```bash
npm run build
npm run preview
```

## Available design-preview routes
- `/` — Public homepage
- `/search` — Journey search and sample result cards
- `/journeys/:id` — Journey details preview
- `/publish` — Driver journey draft form
- `/login` and `/register` — Authentication screens
- `/dashboard/passenger` — Passenger dashboard preview
- `/dashboard/driver` — Driver dashboard preview
- `/admin` — Admin dashboard preview

The Phase 2 website is a navigable, responsive UI prototype. Sample journeys, profiles, ratings and dashboard metrics are illustrative. Search does not query a live API. Authentication, verification, publishing, bookings, messages and admin actions are not connected to the backend yet. No payments are collected or settled. See `docs/PHASE_2_UI_MAP.md` for scope and limitations.
