# Phase 3 — Authentication and User Management

## Implemented account model
- Email is the login identifier and is stored in lowercase.
- Mobile number is stored in international E.164-style format (example: +919876543210).
- Initial roles: passenger and driver. Admin access is managed through Django staff/superuser permissions.
- Terms acceptance timestamp is stored at registration.
- Email and phone verification flags are stored separately.

## API endpoints
All endpoints are under `/api/v1/auth/`.

| Method | Path | Authentication | Purpose |
|---|---|---|---|
| POST | `register/` | Public, throttled | Create a Passenger or Driver account and issue verification codes |
| POST | `verification/request/` | Public, throttled | Request a new code for email or phone |
| POST | `verification/confirm/` | Public, throttled | Confirm a six-digit code |
| POST | `login/` | Public, throttled | Return JWT tokens after both channels are verified |
| POST | `token/refresh/` | Public | Refresh an access token |
| GET | `me/` | JWT | Return the authenticated account profile |

## OTP safeguards
- Codes are six digits, hashed before being stored and never returned by the API.
- Codes expire after ten minutes.
- A code is limited to five incorrect attempts.
- Re-send requests have a sixty-second cooldown.
- Email delivery uses Django's console backend locally and SMTP configuration in production.
- Phone codes are only logged in the Django console when DEBUG and SMS_OTP_CONSOLE are both enabled.
- Production phone verification is not operational until an approved SMS gateway adapter is integrated.

## JWT policy
- Access token: ten minutes.
- Refresh token: seven days.
- Refresh rotation: enabled.
- The current browser client keeps tokens in memory only. A full page refresh requires signing in again. Before production, replace this with a reviewed secure browser/session strategy and add protected route enforcement.

## Privacy and security
- Passwords use Django's password hashing and configured password validators.
- Login is rate-limited; registration and OTP endpoints have scoped throttles.
- Verification records store only password-hashed OTPs.
- The `/me/` endpoint requires a valid JWT.
- CORS must be restricted to the actual production website origin.
- Do not expose OTPs, passwords, document contents or private user data in logs or API responses.

## Not included in this phase
- Social login.
- Password reset workflow.
- Refresh-token revocation/blacklisting.
- User profile editing.
- Admin role assignment through public registration.
- SMS provider integration.
- Protected route middleware for every dashboard route.
- Production cookie-based token/session handling.
