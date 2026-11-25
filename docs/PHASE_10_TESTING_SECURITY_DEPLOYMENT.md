# Phase 10 — Testing, Security and Deployment Readiness

## Scope
Phase 10 hardens the Django production configuration, improves refresh-token lifecycle controls, guards workspace routes by authenticated role, and adds CI checks for Django's deployment security warnings.

This phase prepares the repository for a controlled deployment. It does not claim that the live Render services have been deployed, configured or penetration-tested.

## Security changes

### Production configuration
When `DJANGO_DEBUG=false`, the API now refuses to start unless:
- `DJANGO_SECRET_KEY` is at least 50 characters and is not the development fallback.
- `DJANGO_ALLOWED_HOSTS` contains explicit hostnames and no wildcard.
- `DATABASE_URL` is configured and resolves to PostgreSQL.
- `CORS_ALLOWED_ORIGINS` contains exact frontend origins without wildcards.
- `CSRF_TRUSTED_ORIGINS` is configured.
- HTTPS redirect is enabled and HSTS is enabled.

Production defaults also enable secure session/CSRF cookies, content-type sniffing protection, a strict referrer policy, same-origin opener policy and clickjacking protection. Reverse-proxy HTTPS detection uses `X-Forwarded-Proto` by default; disable that only when the deployment topology requires a different arrangement.

Phone OTP console logging is forced off whenever DEBUG is false, even if an old environment variable still says true. No SMS provider is added in this phase.

### JWT lifecycle
- Refresh tokens rotate.
- Rotated refresh tokens are blacklisted.
- `POST /api/v1/auth/token/blacklist/` revokes a refresh token on sign-out.
- Browser sign-out clears in-memory tokens immediately and attempts server-side refresh-token revocation.
- Access tokens are short-lived (10 minutes); a copied access token can remain valid until it expires.

The browser continues to keep access and refresh tokens in JavaScript memory only. This avoids persistent localStorage storage but means a full page reload requires signing in again. A production session design using an appropriately secured HttpOnly cookie or backend-for-frontend architecture remains a launch prerequisite; do not move refresh tokens into localStorage as a shortcut.

### Workspace route access
The shared dashboard layout calls the authenticated profile endpoint before rendering any passenger, driver or admin workspace. It redirects unauthenticated users to sign-in and redirects a user attempting to open another role's workspace to their own workspace. API permissions remain the actual security boundary; frontend route checks are defence-in-depth only.

### API throttling and files
- Staff analytics/monitoring endpoints use the `admin_read` throttle scope (120 requests/minute).
- Existing registration, login, OTP, booking, finance, messaging and safety scopes remain configured.
- Driver documents continue to use authenticated download endpoints, non-cacheable private responses and extension/content-type/signature/size validation. Do not serve the media directory publicly.
- The current upload signature check is not malware scanning. Add private-storage malware scanning and an operational review process before accepting real identity documents.

## CI
GitHub Actions runs:
1. Frontend TypeScript check and Vite production build.
2. Django system checks.
3. Django `check --deploy` with production-like environment variables.
4. Migration consistency check.
5. Backend test suite.

Run locally:
```bash
cd backend
python manage.py check
python manage.py check --deploy
python manage.py makemigrations --check --dry-run
python manage.py test
```

The production check requires real production environment variables. Do not reuse CI placeholder values in a deployed service.

## Render deployment layout

WayTogether is a monorepo. Create a separate Render Web Service for the Django API and a Static Site for the Vite frontend.

### Django API Web Service
- Repository: `Nithesh17122004/WayTogether`
- Root Directory: `backend`
- Runtime: Python
- Build Command: `pip install -r requirements.txt && python manage.py collectstatic --noinput`
- Start Command: `gunicorn config.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
- Pre-Deploy Command, when available: `python manage.py migrate --noinput`

Use Render PostgreSQL and provide its internal connection string as `DATABASE_URL`. Where a pre-deploy command is unavailable, run migrations as an explicit release step before directing traffic to the new code. Avoid making multiple web instances run schema changes concurrently.

### Vite frontend Static Site
- Repository: `Nithesh17122004/WayTogether`
- Root Directory: `frontend`
- Build Command: `npm install && npm run build`
- Publish Directory: `dist`
- Build-time variable: `VITE_API_BASE_URL=https://YOUR-API-HOST/api/v1`

Configure the actual API and frontend URLs in both services; do not leave localhost values in the production frontend build.

### Required API environment variables
| Variable | Production setting |
|---|---|
| `DJANGO_DEBUG` | `false` |
| `DJANGO_SECRET_KEY` | Unique random secret, 50+ characters |
| `DJANGO_ALLOWED_HOSTS` | Exact API hostname(s), comma-separated |
| `DATABASE_URL` | Render PostgreSQL internal URL |
| `CORS_ALLOWED_ORIGINS` | Exact HTTPS frontend origin(s) |
| `CSRF_TRUSTED_ORIGINS` | Exact HTTPS origins used for Django admin/session requests |
| `DJANGO_SECURE_SSL_REDIRECT` | `true` |
| `DJANGO_SECURE_PROXY_SSL_HEADER` | `true` behind Render's HTTPS proxy |
| `DJANGO_SECURE_HSTS_SECONDS` | `31536000` after HTTPS is confirmed |
| `EMAIL_BACKEND` | Production SMTP backend |
| `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD` | Approved SMTP details |
| `SMS_OTP_CONSOLE` | `false`; console OTP logging is disabled in production regardless |
| `FINANCE_SANDBOX_ENABLED` | `false` |
| `MEDIA_ROOT` | Path on a private persistent disk, e.g. `/var/data/waytogether-media` |
| `MAPS_USER_AGENT` | App identity with monitored contact details |
| `NOMINATIM_URL` | Approved geocoding endpoint |
| `OSRM_ROUTE_URL` | Approved road-routing service; optional |

Keep HSTS subdomain/preload settings disabled until every affected subdomain is HTTPS-ready. Never expose `MEDIA_ROOT` as a static site or public media route.

## Launch gates not solved by this code phase

Do not treat a successful CI run as permission to open public registration or live operations. The following remain external integration or operational requirements:

1. **Phone verification:** connect and test an approved SMS OTP provider. The current production phone verification flow deliberately refuses to log OTPs and reports delivery as unavailable until a provider is integrated.
2. **Secure browser session:** replace the current in-memory bearer-token strategy with a reviewed HttpOnly/SameSite cookie or BFF session design before production launch. Do not persist refresh tokens in localStorage.
3. **Private document storage:** provision a private persistent disk or private object storage, test access controls, backup/restore, deletion and retention. Add malware scanning before real identity documents are accepted.
4. **Shared cache:** the geocoding cache/rate-limit is process-local by default. Use a shared cache such as Redis before running multiple API instances so the global rate limit is enforced across the deployment.
5. **Operations:** configure SMTP, monitored support contact, uptime/error monitoring, database backups, restore drills, retention policies and incident-response ownership.
6. **Product/legal readiness:** obtain applicable transport, insurance, tax, privacy and payment-provider review. Real payments, platform commission, driver payouts and real refunds remain disabled/out of scope.

## Manual release verification
Before launch, test with non-production accounts and documents:
- Register passenger and driver accounts; verify email and phone through configured providers.
- Confirm sign-in fails before both verification channels are complete.
- Confirm a passenger cannot open driver/admin workspaces and a driver cannot open passenger/admin workspaces.
- Confirm sign-out blacklists the refresh token and the same refresh token cannot be reused.
- Upload allowed and disallowed file types; test file size limits, private storage and cross-user download denial.
- Review driver/vehicle approval and published-journey eligibility.
- Test route search, booking approval, seat-capacity race behaviour, cancellation and closed message threads.
- Test private notification ownership, emergency-contact privacy, safety-report permissions and post-completion review eligibility.
- Confirm final expense allocations reconcile and sandbox payments remain simulation-only.
- Confirm staff-only admin APIs reject non-staff users.
- Restore a database backup in a non-production environment.

## Deployment source references
Render's current deployment documentation describes web-service build/pre-deploy/start commands, monorepo root directories, static-site build/publish settings and persistent-disk behaviour:
- https://render.com/docs/deploys
- https://render.com/docs/your-first-deploy
- https://render.com/docs/deploy-django
