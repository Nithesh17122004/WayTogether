# Phase 2 — Website screen map

This phase creates navigable, responsive website layouts for the major WayTogether user journeys.

## Public routes
- `/` — Premium landing page, route examples, explanation and safety positioning.
- `/search` — Search form, filters, example result cards and sample-only notice.
- `/journeys/:id` — Journey information, map placeholder and expense contribution preview.
- `/publish` — Journey draft form and mandatory independently-planned-journey attestation.
- `/login` — Sign-in UI.
- `/register` — Account creation UI.

## Workspace routes
- `/dashboard/passenger` — Passenger overview, booking preview and discovery links.
- `/dashboard/driver` — Driver overview, journey drafts and the cost-sharing principle.
- `/admin` — Admin metrics and verification queue preview.

## Prototype limitations
- All journey cards, account information, dashboard metrics and verification records are illustrative sample data.
- Search filtering operates only on the locally-defined example cards. It is not connected to geocoding, a live database or route matching.
- Login, registration, journey publication, booking requests, messaging, verification and administrative actions are not connected to APIs.
- No payment details are collected and no money is charged or paid out.
- The map is a static visual placeholder; map tiles, directions and geocoding are not integrated yet.
- This phase is a front-end design and navigation milestone, not a launch-ready marketplace.

## Visual QA targets
- Desktop: 1440px and 1280px widths.
- Tablet: 768px and 820px widths.
- Mobile: 390px and 360px widths.
- Keyboard focus visibility, accessible labels, semantic forms and reduced-motion support.
