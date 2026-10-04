"""
Django settings for Ticket platform.

Values are loaded from environment variables (via python-decouple / .env file).
"""

from pathlib import Path

import structlog
from decouple import Csv, config

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Core
# ---------------------------------------------------------------------------
SECRET_KEY: str = config("DJANGO_SECRET_KEY", default="change-me-in-production-use-a-long-random-string")  # type: ignore[assignment]
DEBUG: bool = config("DEBUG", default=False, cast=bool)  # type: ignore[assignment]
ALLOWED_HOSTS: list[str] = config("ALLOWED_HOSTS", default="localhost,127.0.0.1", cast=Csv())  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    "channels",
    "django_celery_beat",
]

LOCAL_APPS = [
    "apps.accounts",
    "apps.organizations",
    "apps.venues",
    "apps.events",
    "apps.inventory",
    "apps.reservations",
    "apps.orders",
    "apps.payments",
    "apps.tickets",
    "apps.checkins",
    "apps.promotions",
    "apps.notifications",
    "apps.analytics",
    "apps.audit",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

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
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------
import dj_database_url  # noqa: E402

_default_db = "postgresql://ticket:ticket@localhost:5432/ticket"
DATABASES = {
    "default": dj_database_url.config(
        env="DATABASE_URL",
        default=config("DATABASE_URL", default=_default_db),  # type: ignore[arg-type]
    )
}
DATABASES["default"]["ATOMIC_REQUESTS"] = True
DATABASES["default"]["CONN_MAX_AGE"] = config("DB_CONN_MAX_AGE", default=60, cast=int)  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Custom User Model (must be set before first migration)
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

# ---------------------------------------------------------------------------
# Password validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & media files
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "mediafiles"

# ---------------------------------------------------------------------------
# Default primary key field type
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Cache / Redis
# ---------------------------------------------------------------------------
REDIS_URL: str = config("REDIS_URL", default="redis://localhost:6379/0")  # type: ignore[assignment]

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "default"

# ---------------------------------------------------------------------------
# Celery
# ---------------------------------------------------------------------------
CELERY_BROKER_URL: str = config("CELERY_BROKER_URL", default=REDIS_URL)  # type: ignore[assignment]
CELERY_RESULT_BACKEND: str = config("CELERY_RESULT_BACKEND", default=REDIS_URL)  # type: ignore[assignment]
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = "UTC"
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 minutes hard limit
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60

# ---------------------------------------------------------------------------
# Django Channels
# ---------------------------------------------------------------------------
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [REDIS_URL],
        },
    },
}

# ---------------------------------------------------------------------------
# Django REST Framework
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "100/hour",
        "user": "1000/hour",
        "login": "10/minute",
        "hold": "30/minute",
        "checkin": "60/minute",
    },
    "EXCEPTION_HANDLER": "config.exceptions.custom_exception_handler",
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
}

# ---------------------------------------------------------------------------
# Simple JWT
# ---------------------------------------------------------------------------
from datetime import timedelta  # noqa: E402

SIMPLE_JWT = {
    "CHECK_REVOKE_TOKEN": True,
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# ---------------------------------------------------------------------------
# CORS
# ---------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS: list[str] = config(  # type: ignore[assignment]
    "CORS_ALLOWED_ORIGINS",
    default="http://localhost:5173,http://localhost:3000",
    cast=Csv(),
)
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS: list[str] = config(  # type: ignore[assignment]
    "CSRF_TRUSTED_ORIGINS",
    default="http://localhost:5173,http://localhost:3000",
    cast=Csv(),
)

# ---------------------------------------------------------------------------
# drf-spectacular (OpenAPI)
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "Ticket API",
    "DESCRIPTION": "Event management and ticketing platform API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": "/api/v1/",
    "COMPONENT_SPLIT_REQUEST": True,
    "SORT_OPERATIONS": False,
}

# ---------------------------------------------------------------------------
# Email
# ---------------------------------------------------------------------------
EMAIL_BACKEND = config("EMAIL_BACKEND", default="django.core.mail.backends.smtp.EmailBackend")  # type: ignore[assignment]
EMAIL_HOST: str = config("EMAIL_HOST", default="localhost")  # type: ignore[assignment]
EMAIL_PORT: int = config("EMAIL_PORT", default=1025, cast=int)  # type: ignore[assignment]
EMAIL_USE_TLS: bool = config("EMAIL_USE_TLS", default=False, cast=bool)  # type: ignore[assignment]
EMAIL_HOST_USER: str = config("EMAIL_HOST_USER", default="")  # type: ignore[assignment]
EMAIL_HOST_PASSWORD: str = config("EMAIL_HOST_PASSWORD", default="")  # type: ignore[assignment]
DEFAULT_FROM_EMAIL: str = config("DEFAULT_FROM_EMAIL", default="Ticket <noreply@ticket.local>")  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# Payment providers
# ---------------------------------------------------------------------------
PAYMENT_PROVIDER: str = config("PAYMENT_PROVIDER", default="mock")  # type: ignore[assignment]  # "mock" or "stripe_test"
STRIPE_ENABLED: bool = config("STRIPE_ENABLED", default=False, cast=bool)  # type: ignore[assignment]
STRIPE_SECRET_KEY: str = config("STRIPE_SECRET_KEY", default="")  # type: ignore[assignment]
STRIPE_WEBHOOK_SECRET: str = config("STRIPE_WEBHOOK_SECRET", default="")  # type: ignore[assignment]
STRIPE_PUBLISHABLE_KEY: str = config("STRIPE_PUBLISHABLE_KEY", default="")  # type: ignore[assignment]

# ---------------------------------------------------------------------------
# App settings
# ---------------------------------------------------------------------------
APP_BASE_URL: str = config("APP_BASE_URL", default="http://localhost:8000")  # type: ignore[assignment]
API_BASE_URL: str = config("API_BASE_URL", default="http://localhost:8000/api/v1")  # type: ignore[assignment]
RESERVATION_HOLD_MINUTES: int = config("RESERVATION_HOLD_MINUTES", default=10, cast=int)  # type: ignore[assignment]
TICKET_QR_SECRET_BYTES: int = 32  # 256-bit entropy

# ---------------------------------------------------------------------------
# Security (tighten in production)
# ---------------------------------------------------------------------------
if not DEBUG:
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_SSL_REDIRECT = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True

# ---------------------------------------------------------------------------
# Logging (structured)
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "json": {
            "()": "structlog.stdlib.ProcessorFormatter",
            "processor": structlog.dev.ConsoleRenderer() if DEBUG else structlog.processors.JSONRenderer(),
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "apps": {
            "handlers": ["console"],
            "level": "DEBUG" if DEBUG else "INFO",
            "propagate": False,
        },
    },
}
