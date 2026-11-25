# WayTogether API

## Requirements
- Python 3.11 or newer
- PostgreSQL for shared development/production; SQLite is used by default locally.

## Setup
```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Health check: http://127.0.0.1:8000/api/v1/health/

## Authentication API (Phase 3)

All endpoints are prefixed with `/api/v1/auth/`.

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `register/` | Create Passenger or Driver account |
| POST | `verification/request/` | Request email or phone OTP |
| POST | `verification/confirm/` | Confirm a six-digit OTP |
| POST | `login/` | Obtain JWT access and refresh tokens |
| POST | `token/refresh/` | Refresh an access token |
| GET | `me/` | Read the authenticated profile |

## Driver and vehicle verification API (Phase 4)

All endpoints are prefixed with `/api/v1/drivers/`. Driver endpoints require a signed-in, active Driver account with both email and mobile verified. Administrator endpoints require Django staff access.

| Method | Endpoint | Purpose |
|---|---|---|
| GET / PATCH | `profile/` | Read or update the current driver's profile |
| GET / POST | `vehicles/` | List or register the current driver's vehicles |
| GET | `vehicles/{id}/` | Read an owned vehicle |
| GET / POST | `documents/` | List or upload private verification documents |
| GET | `documents/{id}/download/` | Download a document after ownership/staff permission check |
| POST | `verification/submit/` | Submit one owned vehicle and driver documents for review |
| GET | `admin/verification/queue/` | Staff-only pending document queue |
| POST | `admin/verification/documents/{id}/review/` | Staff-only approve/reject decision |

### Vehicle registration payload
```json
{
  "registration_number": "TN01AB1234",
  "make": "Honda",
  "model": "City",
  "manufacture_year": 2022,
  "colour": "Blue",
  "vehicle_type": "sedan",
  "passenger_seats": 3,
  "private_use_attested": true
}
```

A vehicle cannot be registered through this workflow unless the driver confirms it is privately used and is not being registered as a commercial taxi.

### Document upload
Send a multipart form request to `/documents/`:
- `document_type`: `driver_license`, `vehicle_registration`, `insurance`, `pollution_certificate` or `vehicle_photo`.
- `vehicle`: required for all vehicle document types and must belong to the authenticated driver. Omit for `driver_license`.
- `file`: PDF, JPG, JPEG or PNG, up to 8 MB.
- `expiry_date`: optional date in ISO format where applicable.

Driving licence, vehicle registration certificate, insurance certificate and vehicle photograph are required before a vehicle can be submitted. Pollution certificate is supported as an additional document where applicable.

### Submit a vehicle
```json
{ "vehicle_id": 12 }
```

### Administrator review
```json
{ "decision": "rejected", "review_note": "Please upload a clearer copy." }
```
Use `decision: "approved"` to approve a document. A rejection reason is mandatory. Once required documents have been individually approved, the vehicle and driver verification statuses are recalculated.

## Private document storage and production notes
- Files are stored under the private `MEDIA_ROOT/private/driver-verification/` path in local development.
- The API never returns a public media URL. Downloads go through the authenticated endpoint; owners and Django staff can download, other users receive 404.
- Do not map `MEDIA_ROOT` or `MEDIA_URL` to a public web server route.
- Before production, configure persistent private object storage (for example, a private S3-compatible bucket) or a private persistent volume and test access controls, backup, retention and deletion.
- Configure malware scanning and operational review procedures before accepting real identity/vehicle documents in production.
- Review document retention, privacy notices and access logging with the company's legal/privacy advisers.

## Local OTP delivery
- Email OTPs are printed by Django's console email backend while `DJANGO_DEBUG=true`.
- Phone OTPs are logged by Django only when `SMS_OTP_CONSOLE=true` and `DJANGO_DEBUG=true`.
- Never expose OTP values in API responses.
- Production phone verification requires an approved SMS provider.

## Security notes
- Use a unique, high-entropy `DJANGO_SECRET_KEY` in production.
- Configure `DATABASE_URL`, allowed hosts, HTTPS, CORS and SMTP through deployment secrets.
- JWT access tokens expire after ten minutes; refresh tokens expire after seven days.
- The website currently keeps JWTs in memory. A production-grade browser token/session strategy and route guards remain required before launch.
