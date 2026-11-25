# Phase 8 — Communication, safety and trust

## Purpose
Provide booking-linked communication, account-scoped notifications, private emergency-contact storage, safety reporting and booking-verified post-journey reviews.

## Booking messages
- One thread per booking.
- Passenger and owning Driver are the only participants.
- Pending and confirmed booking threads are writable before the scheduled departure while the journey remains published.
- Thread history remains readable after cancellation or completion but becomes read-only.
- Text only, maximum 1,500 characters per message; no attachments.
- Messages are immutable once sent.
- Rate limit: 30 messages/API requests per hour.
- Do not send OTPs, passwords, payment credentials or other highly sensitive information.

## Notifications
In-app notification events are created for:
- New booking request.
- Booking confirmed or declined.
- Booking cancellation or journey cancellation.
- New message.
- Final passenger expense contribution created.
- Safety report status update.

Each notification belongs to one recipient account. A user can list their newest 100 notifications, mark one as read or mark all their notifications as read. This phase does not integrate external email, SMS or push delivery.

## Emergency contacts
- Account owner can store up to three contact records.
- Phone numbers use international format.
- Contact details are visible only to the owner account.
- A contact is not sent an invitation or notification; no call/SMS/share-trip action is performed.
- The product does not automatically reveal these details to a booking participant.

## Safety reports
- A report must be linked to a booking or journey in which the reporter participated.
- A named reported user must be another participant in that journey.
- The reporter can list only their own reports.
- Only staff administrators can access the report queue and internal notes.
- Staff can update status (open, reviewing, resolved, closed) and a private note. The reporter receives an in-app status notification but not the private note.
- Categories cover unsafe driving, harassment/inappropriate behaviour, profile/journey misrepresentation, expense contribution disputes, accident/injury and other safety concerns.
- Urgent priority is a review label only; it does not dispatch help or notify emergency services.

**Emergency limitation:** The platform is not an emergency service. In immediate danger or a medical emergency, contact local emergency services directly. The safety report form is for platform review only.

## Journey reviews
- A review can be submitted only by the passenger or driver on a confirmed booking.
- The journey must have reached completed status.
- Each participant may review the other participant once per booking.
- Rating range: 1–5; comment optional, maximum 1,000 characters.
- Review listing endpoints are limited to the current account's written or received reviews.
- This phase does not calculate a public rating score or alter journey search ranking.

## Frontend routes
Passenger:
- `/dashboard/passenger/messages`
- `/dashboard/passenger/notifications`
- `/dashboard/passenger/safety`
- `/dashboard/passenger/reviews`

Driver:
- `/dashboard/driver/messages`
- `/dashboard/driver/notifications`
- `/dashboard/driver/safety`
- `/dashboard/driver/reviews`

Administrator:
- `/admin/safety`

## API prefix
All endpoints use `/api/v1/trust/`. See `backend/README.md` for the complete endpoint matrix.

## Not included
- Live trip location tracking or contact share links.
- SOS button, automatic emergency calls or ambulance/police integration.
- Email/SMS/push notification sending.
- Message attachments, editing or deletion.
- Automated content moderation or dispute adjudication.
- Public reviews, public star scores or automatic trust ranking.
