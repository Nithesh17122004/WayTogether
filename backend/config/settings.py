import os
from datetime import timedelta
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _env_bool(name, default):
    value = os.getenv(name)
    if value is None:
        return default
    normalised = value.strip().lower()
    if normalised in {"1", "true", "yes", "on"}:
        return True
    if normalised in {"0", "false", "no", "off"}:
        return False
    raise ImproperlyConfigured(f"{name} must be set to true or false.")


DEBUG = _env_bool("DJANGO_DEBUG", True)
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "development-only-change-this-secret").strip()
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]
# Render sets this automatically for each deployed web service.
# Include it so Django accepts the service's generated hostname even when
# DJANGO_ALLOWED_HOSTS has not been updated after a service URL changes.
render_external_hostname = os.getenv("RENDER_EXTERNAL_HOSTNAME", "").strip()
if render_external_hostname and render_external_hostname not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append(render_external_hostname)
CORS_ALLOWED_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv("CORS_ALLOWED_ORIGINS", "http://localhost:5173").split(",")
    if origin.strip()
]
CSRF_TRUSTED_ORIGINS = [
    origin.strip().rstrip("/")
    for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
    if origin.strip()
]

if not DEBUG:
    if len(SECRET_KEY) < 50 or SECRET_KEY == "development-only-change-this-secret":
        raise ImproperlyConfigured("Set DJANGO_SECRET_KEY to a unique random value of at least 50 characters.")
    if not ALLOWED_HOSTS or "*" in ALLOWED_HOSTS:
        raise ImproperlyConfigured("Set DJANGO_ALLOWED_HOSTS to the exact production API hostnames; wildcards are not allowed.")
    if not DATABASE_URL:
        raise ImproperlyConfigured("DATABASE_URL is required outside development.")
    if not CORS_ALLOWED_ORIGINS or "*" in CORS_ALLOWED_ORIGINS or any(not origin.startswith("https://") for origin in CORS_ALLOWED_ORIGINS):
        raise ImproperlyConfigured("Set CORS_ALLOWED_ORIGINS to exact HTTPS frontend origin(s); wildcards and HTTP origins are not allowed in production.")
    if not CSRF_TRUSTED_ORIGINS or any(not origin.startswith("https://") for origin in CSRF_TRUSTED_ORIGINS):
        raise ImproperlyConfigured("Set CSRF_TRUSTED_ORIGINS to exact HTTPS frontend/admin origin(s) in production.")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "apps.accounts.apps.AccountsConfig",
    "apps.drivers.apps.DriversConfig",
    "apps.journeys.apps.JourneysConfig",
    "apps.bookings.apps.BookingsConfig",
    "apps.finance.apps.FinanceConfig",
    "apps.trust.apps.TrustConfig",
    "apps.core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

database_url = DATABASE_URL or f"sqlite:///{BASE_DIR / 'db.sqlite3'}"
DATABASES = {
    "default": dj_database_url.parse(database_url, conn_max_age=600),
}
if not DEBUG and DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured("Production must use PostgreSQL; SQLite is supported for local development only.")

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-in"
TIME_ZONE = "Asia/Kolkata"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "media/"
MEDIA_ROOT = Path(os.getenv("MEDIA_ROOT") or str(BASE_DIR / "media")).expanduser()

# Passenger identity documents use a dedicated private storage alias. In production,
# uploads are enabled only when the operator explicitly opts in AND all S3-compatible
# credentials are present. Cloudflare R2 is the documented provider; the S3-compatible
# endpoint also allows another private object-storage provider if required.
PRIVATE_MEDIA_BUCKET_NAME = os.getenv("PRIVATE_MEDIA_BUCKET_NAME", "").strip()
PRIVATE_MEDIA_ENDPOINT_URL = os.getenv("PRIVATE_MEDIA_ENDPOINT_URL", "").strip().rstrip("/")
PRIVATE_MEDIA_ACCESS_KEY_ID = os.getenv("PRIVATE_MEDIA_ACCESS_KEY_ID", "").strip()
PRIVATE_MEDIA_SECRET_ACCESS_KEY = os.getenv("PRIVATE_MEDIA_SECRET_ACCESS_KEY", "")
PRIVATE_MEDIA_REGION_NAME = os.getenv("PRIVATE_MEDIA_REGION_NAME", "auto").strip() or "auto"
PRIVATE_MEDIA_S3_CONFIGURED = all((
    PRIVATE_MEDIA_BUCKET_NAME,
    PRIVATE_MEDIA_ENDPOINT_URL,
    PRIVATE_MEDIA_ACCESS_KEY_ID,
    PRIVATE_MEDIA_SECRET_ACCESS_KEY,
))
if PRIVATE_MEDIA_ENDPOINT_URL and not PRIVATE_MEDIA_ENDPOINT_URL.startswith("https://"):
    raise ImproperlyConfigured("PRIVATE_MEDIA_ENDPOINT_URL must use HTTPS.")

# Prevent a manually enabled feature flag from sending sensitive files to Render's
# ephemeral local filesystem. Local development may use a private local folder.
_PRIVATE_MEDIA_OPT_IN = _env_bool("PRIVATE_MEDIA_STORAGE_READY", DEBUG)
PRIVATE_MEDIA_STORAGE_READY = _PRIVATE_MEDIA_OPT_IN and (DEBUG or PRIVATE_MEDIA_S3_CONFIGURED)

if PRIVATE_MEDIA_S3_CONFIGURED:
    # django-storages reads these settings when it creates the private S3 backend.
    # Keep credentials in environment variables; do not pass them in model field
    # declarations or migration files.
    AWS_S3_ACCESS_KEY_ID = PRIVATE_MEDIA_ACCESS_KEY_ID
    AWS_S3_SECRET_ACCESS_KEY = PRIVATE_MEDIA_SECRET_ACCESS_KEY
    AWS_STORAGE_BUCKET_NAME = PRIVATE_MEDIA_BUCKET_NAME
    AWS_S3_ENDPOINT_URL = PRIVATE_MEDIA_ENDPOINT_URL
    AWS_S3_REGION_NAME = PRIVATE_MEDIA_REGION_NAME
    AWS_S3_SIGNATURE_VERSION = "s3v4"
    AWS_S3_ADDRESSING_STYLE = "path"
    AWS_S3_FILE_OVERWRITE = False
    AWS_DEFAULT_ACL = None
    AWS_QUERYSTRING_AUTH = True
    AWS_S3_CUSTOM_DOMAIN = None
    AWS_S3_OBJECT_PARAMETERS = {"CacheControl": "private, no-store"}
    passenger_private_storage = {
        "BACKEND": "storages.backends.s3.S3Storage",
        "OPTIONS": {
            "file_overwrite": False,
            "default_acl": None,
            "querystring_auth": True,
            "querystring_expire": 60,
            "custom_domain": None,
            "object_parameters": {"CacheControl": "private, no-store"},
        },
    }
else:
    passenger_private_storage = {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": str(MEDIA_ROOT / "private-passenger")},
    }

# Verification documents must only be served through the authenticated download API.
# Never expose MEDIA_ROOT or MEDIA_URL through a public static/media route.
DATA_UPLOAD_MAX_MEMORY_SIZE = 12 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
FILE_UPLOAD_PERMISSIONS = 0o640
FILE_UPLOAD_DIRECTORY_PERMISSIONS = 0o750
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "passenger_private": passenger_private_storage,
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# Redis backs shared cache/throttle state in production; local development uses memory.
REDIS_URL = os.getenv("REDIS_URL", "").strip()
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "KEY_PREFIX": "waytogether",
        }
    }
else:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
            "LOCATION": "waytogether-local",
        }
    }

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "accounts.User"

EMAIL_BACKEND = os.getenv(
    "EMAIL_BACKEND",
    "django.core.mail.backends.console.EmailBackend" if DEBUG else "django.core.mail.backends.smtp.EmailBackend",
)
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "").strip()
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = _env_bool("EMAIL_USE_TLS", True)
EMAIL_USE_SSL = _env_bool("EMAIL_USE_SSL", False)
EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "django").strip().lower()
RESEND_API_KEY = os.getenv("RESEND_API_KEY", "").strip()
RESEND_FROM_EMAIL = os.getenv("RESEND_FROM_EMAIL", "").strip()
RESEND_API_URL = "https://api.resend.com/emails"

if EMAIL_PROVIDER not in {"django", "resend"}:
    raise ImproperlyConfigured("EMAIL_PROVIDER must be either 'django' or 'resend'.")
if EMAIL_PROVIDER == "resend" and (not RESEND_API_KEY or not RESEND_FROM_EMAIL):
    raise ImproperlyConfigured(
        "Set RESEND_API_KEY and RESEND_FROM_EMAIL before enabling EMAIL_PROVIDER=resend."
    )
DEFAULT_FROM_EMAIL = os.getenv("DEFAULT_FROM_EMAIL", "").strip() or (
    f"WayTogether <{EMAIL_HOST_USER}>" if EMAIL_HOST_USER else "WayTogether <no-reply@waytogether.in>"
)
# Console OTP logging is always disabled outside DEBUG, even if a stale env value says true.
SMS_OTP_CONSOLE = DEBUG and _env_bool("SMS_OTP_CONSOLE", True)

REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.ScopedRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "register": "5/hour",
        "login": "10/minute",
        "otp": "5/hour",
        "map_search": "30/minute",
        "route_preview": "30/minute",
        "booking_request": "10/hour",
        "booking_action": "30/hour",
        "finance_action": "10/hour",
        "message_send": "30/hour",
        "safety_action": "10/hour",
        "admin_read": "120/minute",
    },
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

SECURE_SSL_REDIRECT = _env_bool("DJANGO_SECURE_SSL_REDIRECT", not DEBUG)
SECURE_PROXY_SSL_HEADER = (
    ("HTTP_X_FORWARDED_PROTO", "https")
    if _env_bool("DJANGO_SECURE_PROXY_SSL_HEADER", not DEBUG)
    else None
)
SECURE_HSTS_SECONDS = int(os.getenv("DJANGO_SECURE_HSTS_SECONDS", "31536000" if not DEBUG else "0"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = _env_bool("DJANGO_SECURE_HSTS_INCLUDE_SUBDOMAINS", False)
SECURE_HSTS_PRELOAD = _env_bool("DJANGO_SECURE_HSTS_PRELOAD", False)
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SAMESITE = "Lax"

if not DEBUG and (not SECURE_SSL_REDIRECT or SECURE_HSTS_SECONDS < 1):
    raise ImproperlyConfigured("Production requires HTTPS redirection and HSTS. Configure the DJANGO_SECURE_* settings.")

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=10),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

NOMINATIM_URL = os.getenv("NOMINATIM_URL", "https://nominatim.openstreetmap.org/search")
OSRM_ROUTE_URL = os.getenv("OSRM_ROUTE_URL", "")
MAPS_USER_AGENT = os.getenv(
    "MAPS_USER_AGENT",
    "WayTogether/1.0 (configure a monitored contact URL before production)",
)

# Razorpay is intentionally restricted to Test Mode until a separately reviewed go-live change.
RAZORPAY_TEST_MODE = _env_bool("RAZORPAY_TEST_MODE", True)
RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID", "").strip()
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET", "")
# Browser-based destructive cleanup is disabled unless explicitly enabled for the one-time admin action.
ADMIN_DATABASE_CLEANUP_ENABLED = _env_bool("ADMIN_DATABASE_CLEANUP_ENABLED", False)
FINANCE_SANDBOX_ENABLED = False
LIVE_PAYMENTS_ENABLED = False
