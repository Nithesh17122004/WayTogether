# WayTogether Product Requirements

## Product definition
WayTogether is a responsive, website-first private carpooling platform. It matches passengers with private car owners who independently planned journeys and wish to share eligible journey expenses.

**Tagline:** Share the same route.

## Product principles
- Genuine pre-planned journeys only.
- Drivers must attest that they would make the journey without passengers.
- Passenger contributions are intended to share eligible journey expenses, not create driver profit.
- Any platform fee must be separately disclosed and enabled only after legal and tax approval.
- Pan-India technical support does not imply nationwide regulatory clearance.
- Live payments and payouts remain disabled pending legal, GST, insurance and payment-provider approval.

## User roles
- Passenger: discover journeys, request seats, manage bookings, communicate, review and report.
- Driver: maintain profile and vehicle, submit verification documents, publish eligible journeys, manage requests.
- Admin: verify users and vehicles, moderate journeys, handle disputes and reports, manage configuration.
- Support: manage help requests and incident escalation.

## MVP scope
1. Public marketing pages and responsive navigation.
2. Email/mobile authentication and profile management.
3. Driver/vehicle information and document verification workflow.
4. Journey creation with origin, destination, stops, date, time, seats and expense contribution.
5. Search and filters.
6. Booking requests, driver approval, seat locking and cancellation.
7. Email/in-app notifications.
8. Reviews after completed journeys.
9. Safety reports and support tickets.
10. Admin dashboard and audit trail.

## Later scope
- Marketplace payments and settlement after approvals.
- Realtime chat and optional location sharing.
- PWA enhancements, Android app, multilingual UX, institutional programmes and advanced route matching.

## Core journey rules
- Driver independently plans the journey and confirms it is not being created to serve passenger demand.
- A journey cannot be published without the required attestation.
- Contributions must comply with the approved expense-sharing policy.
- No surge pricing or profit-seeking driver fares.
- Admin must be able to suspend or remove journeys and accounts.
- Seat availability updates must be transactional to prevent overbooking.
- Reviews are limited to users with completed bookings.

## Key workflows
### Driver publishing
Register -> complete profile -> submit driver and vehicle documents -> admin verification -> create independently planned journey -> add stops and seats -> disclose expense contribution -> publish.

### Passenger booking
Search route and date -> inspect journey and driver -> request seat -> driver accepts/rejects -> passenger receives booking status -> journey occurs -> mark complete -> review.

### Admin verification
Review submitted documents -> approve/reject with reason -> retain audit event -> notify user -> allow resubmission where appropriate.

## Non-functional requirements
- Mobile-first responsive layouts.
- WCAG-aware semantic UI and keyboard navigation.
- Server-side authorization for all protected operations.
- Secure storage and access control for identity/vehicle documents.
- Rate limits for authentication and sensitive endpoints.
- CSRF, CORS, input validation and secure headers.
- Webhook verification and idempotency for future payment integration.
- Audit logging for administrative actions.
- Database backups and operational monitoring.
- Privacy-aware retention and deletion workflows.

## Launch gates
Before real-money operation, obtain documented advice on state-wise aggregator requirements, private vehicle pooling, platform fees, GST treatment, insurance coverage, payment aggregation/split settlement and consumer grievance responsibilities. Keep live payment and payout features disabled until all approvals are in place.
