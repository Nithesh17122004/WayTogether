# WayTogether API

## Requirements
- Python 3.11 or newer
- PostgreSQL for shared development/production; SQLite is used by default locally.

## Setup
```bash
cd backend
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1
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

### Registration payload
```json
{
  "full_name": "Example User",
  "email": "user@example.com",
  "phone": "+919876543210",
  "password": "Use-a-strong-password",
  "role": "passenger",
  "accepted_terms": true
}
```

### Verify an email or phone
```json
{ "email": "user@example.com", "channel": "email", "code": "123456" }
```
Use `channel: "phone"` for mobile verification.

### Login payload
```json
{ "email": "user@example.com", "password": "Use-a-strong-password" }
```

Pass the returned access token as `Authorization: Bearer <access>` when calling `/me/`. Login is blocked until both email and phone are verified. Codes expire after ten minutes; incorrect attempts are limited and resend requests have a cooldown. Rate limits are configured for registration, login and OTP endpoints.

## Local OTP delivery
- Email OTPs are printed by Django's console email backend while `DJANGO_DEBUG=true`.
- Phone OTPs are logged to the Django development console only when `SMS_OTP_CONSOLE=true` and `DJANGO_DEBUG=true`.
- Never expose OTP values in API responses.
- Production phone verification is not enabled until an approved SMS provider is integrated. Do not enable console OTP delivery in production.
- Configure SMTP and a production SMS provider before using real accounts.

## Security notes
- Use a unique, high-entropy `DJANGO_SECRET_KEY` in production.
- Configure `DATABASE_URL`, allowed hosts, HTTPS, CORS and SMTP through deployment secrets.
- JWT access tokens expire after ten minutes; refresh tokens expire after seven days.
- Keep identity documents private when document verification is implemented.
- The website/API still needs protected route enforcement and a production-grade browser token storage strategy before launch.
