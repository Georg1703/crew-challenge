"""Settings shared by every environment.

Values come from environment variables (see the repo's .env.example). Environment-specific files
(local.py, test.py, production.py) import this module and override what differs.

Time rules: the database and the app store instants in UTC (USE_TZ, TIME_ZONE = "UTC").
Crew-local dates are computed with apps.core.clock, never with the server's time zone.
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
REPO_DIR = BASE_DIR.parent

env = environ.Env()
_env_file = REPO_DIR / ".env"
if _env_file.is_file():
    environ.Env.read_env(str(_env_file), overwrite=False)

# --- Core -----------------------------------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY", default="insecure-local-only")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=["http://localhost:5173"])
APP_PUBLIC_URL = env("APP_PUBLIC_URL", default="http://localhost:5173")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "django_celery_beat",
    "apps.core",
    "apps.accounts",
    "apps.crews",
    "apps.challenges",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

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

# --- Database -------------------------------------------------------------------------------
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgres://crew:crew-local-password@localhost:5432/crew_challenges",
    )
}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Auth and sessions ----------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
        "OPTIONS": {"min_length": 8},
    },
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

SESSION_COOKIE_AGE = 60 * 60 * 24 * 365  # one year: people stay logged in on their phones
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_HTTPONLY = False  # the SPA reads it to send X-CSRFToken

# --- Time and language ----------------------------------------------------------------------
USE_TZ = True
TIME_ZONE = "UTC"
DEFAULT_CREW_TIMEZONE = env("DEFAULT_CREW_TIMEZONE", default="Europe/Chisinau")
LANGUAGE_CODE = "en"
LANGUAGES = [("ro", "Romana"), ("en", "English")]
USE_I18N = True

# --- Static files ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# --- Django REST framework ------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["apps.core.authentication.SessionAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.CursorPagination",
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.core.exception_handler.exception_handler",
    "UNAUTHENTICATED_USER": "django.contrib.auth.models.AnonymousUser",
    "DEFAULT_THROTTLE_RATES": {"login": "5/min", "join": "10/min", "invite_preview": "30/min"},
    # How many reverse proxies to trust for X-Forwarded-For (Caddy in production = 1).
    "NUM_PROXIES": env.int("TRUSTED_PROXY_COUNT", default=0),
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Crew Challenges API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "COMPONENT_SPLIT_REQUEST": True,
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]+",
    # Several models have a "state" field; give each enum its own name in the contract.
    "ENUM_NAME_OVERRIDES": {
        "ChallengeStateEnum": "apps.challenges.models.Challenge.State",
        "RoundStateEnum": "apps.challenges.models.Round.State",
    },
}

# --- Redis, cache and Celery ----------------------------------------------------------------
REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")
# Shared cache (rate limits, later short-lived data). Redis so every worker sees the same counts.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("CACHE_URL", default="redis://localhost:6379/3"),
        "TIMEOUT": 300,
    }
}
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default="redis://localhost:6379/1")
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default="redis://localhost:6379/2")
CELERY_TIMEZONE = "UTC"
CELERY_ENABLE_UTC = True
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 1
CELERY_RESULT_EXPIRES = 60 * 60 * 24
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# --- AWS and media storage ------------------------------------------------------------------
# Credentials are never settings: boto3 reads AWS_PROFILE locally or the IAM user's keys from
# the environment in production.
AWS_REGION = env("AWS_REGION", default="eu-central-1")
AWS_PROFILE = env("AWS_PROFILE", default="") or None
MEDIA_BUCKET = env("MEDIA_BUCKET", default="cc-dev-media")
# "s3" in every real environment; "memory" in tests (see integrations/storage).
OBJECT_STORAGE_BACKEND = env("OBJECT_STORAGE_BACKEND", default="s3")

# --- Logging --------------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "plain": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
    "loggers": {
        "django.db.backends": {"level": "WARNING"},
        "botocore": {"level": "WARNING"},
    },
}
