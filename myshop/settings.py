# myshop/settings.py
from pathlib import Path

import os
from datetime import timedelta
from decouple import config, Csv
from corsheaders.defaults import default_headers
from django.utils.translation import gettext_lazy as _
from decimal import Decimal


# --------------------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# --------------------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------------------
def csv_list(name: str, default: str = "") -> list[str]:
    """Split comma/space separated env var into a clean list."""
    raw = os.getenv(name, default)
    return [chunk.strip() for chunk in raw.replace(" ", ",").split(",") if chunk.strip()]

# --------------------------------------------------------------------------------------
# Core
# --------------------------------------------------------------------------------------
SECRET_KEY = config("SECRET_KEY", default="replace-me")
DEBUG = config("DEBUG", cast=bool, default=False)

# Match our API domain
ALLOWED_HOSTS = csv_list("ALLOWED_HOSTS", default="api.sockcs.com,localhost,127.0.0.1")

# Trust reverse proxy (Nginx/ALB)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
USE_X_FORWARDED_HOST = True

# --------------------------------------------------------------------------------------
# Applications
# --------------------------------------------------------------------------------------
INSTALLED_APPS = [
    # Django
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Project apps
    "accounts",
    "shop.apps.ShopConfig",
    "cart.apps.CartConfig",
    "orders.apps.OrdersConfig",
    "payment.apps.PaymentConfig",
    "coupons.apps.CouponsConfig",
    "recommendation",
    "recommender",
    "support",
    "products",
    "customers.apps.CustomersConfig",
    "inventory.apps.InventoryConfig",

    # 3rd-party
    "graphene_django",
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "django_filters",
    "django_bootstrap5",
    "rosetta",
]

# --------------------------------------------------------------------------------------
# Middleware
# --------------------------------------------------------------------------------------
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",


    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "myshop.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "cart.context_processors.cart_items_count",
                "shop.context_processors.category_list",
            ],
        },
    },
]

WSGI_APPLICATION = "myshop.wsgi.application"

# --------------------------------------------------------------------------------------
# Database (env-driven)
# --------------------------------------------------------------------------------------
ENGINE = config("DB_ENGINE", default="django.db.backends.sqlite3")

if ENGINE.endswith("mysql"):
    DATABASES = {
        "default": {
            "ENGINE": ENGINE,
            "NAME": config("DB_NAME"),
            "USER": config("DB_USER"),
            "PASSWORD": config("DB_PASSWORD"),
            "HOST": config("DB_HOST"),
            "PORT": config("DB_PORT", default="3306"),
            "OPTIONS": {"charset": "utf8mb4"},
        }
    }
elif ENGINE.endswith("postgresql") or ENGINE.endswith("postgresql_psycopg2"):
    DATABASES = {
        "default": {
            "ENGINE": ENGINE,
            "NAME": config("DB_NAME"),
            "USER": config("DB_USER"),
            "PASSWORD": config("DB_PASSWORD"),
            "HOST": config("DB_HOST", default="localhost"),
            "PORT": config("DB_PORT", default="5432"),
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

# --------------------------------------------------------------------------------------
# Auth / Users
# --------------------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["django.contrib.auth.backends.ModelBackend"]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --------------------------------------------------------------------------------------
# i18n / l10n
# --------------------------------------------------------------------------------------
LANGUAGE_CODE = "en"
LANGUAGES = [("en", _("English")), ("es", _("Spanish"))]
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True
LOCALE_PATHS = [BASE_DIR / "locale"]

# --------------------------------------------------------------------------------------
# Static / Media
# --------------------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = config("STATIC_ROOT", default=str(BASE_DIR / "staticfiles"))

# Serve media via absolute API URL
MEDIA_URL = config("MEDIA_URL", default="https://api.sockcs.com/media/")
MEDIA_ROOT = config("MEDIA_ROOT", default=str(BASE_DIR / "media"))

# --------------------------------------------------------------------------------------
# CORS / CSRF
# --------------------------------------------------------------------------------------
CORS_ALLOWED_ORIGINS = csv_list(
    "CORS_ALLOWED_ORIGINS",
    default="https://sockcs.com,https://www.sockcs.com,https://api.sockcs.com"
)
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https://socks-[a-z0-9-]+\.vercel\.app$",  # Vercel preview URLs
]

CORS_ALLOW_HEADERS = list(default_headers) + [
"cache-control", "x-csrftoken", "authorization", "pragma",
]


CORS_ALLOW_CREDENTIALS = True

CSRF_TRUSTED_ORIGINS = csv_list(
    "CSRF_TRUSTED_ORIGINS",
    default="https://sockcs.com,https://www.sockcs.com,https://api.sockcs.com"
)

# ✅ Critical for sharing cookies across apex + subdomain
SESSION_COOKIE_DOMAIN = ".sockcs.com"
CSRF_COOKIE_DOMAIN   = ".sockcs.com"

SESSION_COOKIE_SAMESITE = "None"
CSRF_COOKIE_SAMESITE = "None"
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG

SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 7  # 7 days
SESSION_SAVE_EVERY_REQUEST = True
SESSION_SERIALIZER = "django.contrib.sessions.serializers.JSONSerializer"


CART_SESSION_ID = "cart"


# --------------------------------------------------------------------------------------
# DRF / JWT
# --------------------------------------------------------------------------------------
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
        "rest_framework.authentication.TokenAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
}

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=30),
    "ROTATE_REFRESH_TOKENS": False,
    "BLACKLIST_AFTER_ROTATION": True,
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}

# --------------------------------------------------------------------------------------
# Email
# --------------------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = config("EMAIL_HOST", default="smtp.hostinger.com")
EMAIL_PORT = config("EMAIL_PORT", cast=int, default=587)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_SSL = config("EMAIL_USE_SSL", cast=bool, default=True)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default=EMAIL_HOST_USER or "noreply@sockcs.com")
SERVER_EMAIL = config("SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)

# --------------------------------------------------------------------------------------
# Stripe / Graphene / Misc
# --------------------------------------------------------------------------------------
STRIPE_PUBLISHABLE_KEY = config("STRIPE_PUBLISHABLE_KEY", default="")
STRIPE_SECRET_KEY = config("STRIPE_SECRET_KEY", default="")
STRIPE_API_VERSION = config("STRIPE_API_VERSION", default="2024-04-10")
STRIPE_WEBHOOK_SECRET = config("STRIPE_WEBHOOK_SECRET", default="")

GRAPHENE = {"SCHEMA": "recommender.schema.schema"}

OLLAMA_HOST = config("OLLAMA_HOST", default="http://127.0.0.1:11434")
OLLAMA_MODEL = config("OLLAMA_MODEL", default="llama3:8b-instruct-q4_0")
OLLAMA_TIMEOUT = config("OLLAMA_TIMEOUT", cast=int, default=12)

SITE_NAME = config("SITE_NAME", default="Sockcs Shop")
SITE_DOMAIN = config("SITE_DOMAIN", default="sockcs.com")
FRONTEND_URL = config("FRONTEND_URL", default="https://sockcs.com")

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --------------------------------------------------------------------------------------
# Security
# --------------------------------------------------------------------------------------
if not DEBUG:
    SECURE_HSTS_SECONDS = config("SECURE_HSTS_SECONDS", cast=int, default=31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_BROWSER_XSS_FILTER = True
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    X_FRAME_OPTIONS = "DENY"

# --------------------------------------------------------------------------------------
# Logging
# --------------------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
    "loggers": {
        "django.request": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
REDIS_HOST = '127.0.0.1' 
REDIS_PORT = 6379          
REDIS_DB   = 0   # <--- add this line


TAX_RATES = {
    # Your originals
    "NY": Decimal("0.08875"),  # NYC combined (you set this)
    "NJ": Decimal("0.06625"),
    "CA": Decimal("0.0725"),

    # Rest of states + DC (baseline statewide rates)
    "AL": Decimal("0.0400"),
    "AK": Decimal("0.0000"),
    "AZ": Decimal("0.0560"),
    "AR": Decimal("0.0650"),
    "CO": Decimal("0.0290"),
    "CT": Decimal("0.0635"),
    "DE": Decimal("0.0000"),
    "DC": Decimal("0.0600"),
    "FL": Decimal("0.0600"),
    "GA": Decimal("0.0400"),
    "HI": Decimal("0.0400"),
    "ID": Decimal("0.0600"),
    "IL": Decimal("0.0625"),
    "IN": Decimal("0.0700"),
    "IA": Decimal("0.0600"),
    "KS": Decimal("0.0650"),
    "KY": Decimal("0.0600"),
    "LA": Decimal("0.0445"),
    "ME": Decimal("0.0550"),
    "MD": Decimal("0.0600"),
    "MA": Decimal("0.0625"),
    "MI": Decimal("0.0600"),
    "MN": Decimal("0.06875"),
    "MS": Decimal("0.0700"),
    "MO": Decimal("0.04225"),
    "MT": Decimal("0.0000"),
    "NE": Decimal("0.0550"),
    "NV": Decimal("0.0685"),
    "NH": Decimal("0.0000"),
    "NM": Decimal("0.05125"),
    "NC": Decimal("0.0475"),
    "ND": Decimal("0.0500"),
    "OH": Decimal("0.0575"),
    "OK": Decimal("0.0450"),
    "OR": Decimal("0.0000"),
    "PA": Decimal("0.0600"),
    "RI": Decimal("0.0700"),
    "SC": Decimal("0.0600"),
    "SD": Decimal("0.0450"),
    "TN": Decimal("0.0700"),
    "TX": Decimal("0.0625"),
    "UT": Decimal("0.0485"),
    "VT": Decimal("0.0600"),
    "VA": Decimal("0.0430"),
    "WA": Decimal("0.0650"),
    "WV": Decimal("0.0600"),
    "WI": Decimal("0.0500"),
    "WY": Decimal("0.0400"),
}
