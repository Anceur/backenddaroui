import os
from pathlib import Path
from datetime import timedelta
# Deployment imports
# import dj_database_url
# Cloudinary imports (commented out - using local storage)
# import cloudinary
# import cloudinary.uploader
# import cloudinary.api

# ==========================
# BASE DIR
# ==========================
BASE_DIR = Path(__file__).resolve().parent.parent

# ==========================
# SECURITY
# ==========================
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "unsafe-secret")
DEBUG = os.environ.get("DJANGO_DEBUG", "True").lower() in ("1", "true", "yes")

ALLOWED_HOSTS = os.environ.get(
    "ALLOWED_HOSTS",
    "*"
).split(",")

# ==========================
# INSTALLED APPS
# ==========================
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "main",

    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",

    "corsheaders",
    "channels",

    # Cloudinary apps (commented out - using local storage)
    # "cloudinary",
    # "cloudinary_storage",
]

# ==========================
# MIDDLEWARE
# ==========================
MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # Deployment middleware (commented for local development)
    # "whitenoise.middleware.WhiteNoiseMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",

    "main.middleware.RefreshTokenMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ==========================
# URL / WSGI / ASGI
# ==========================
ROOT_URLCONF = "backend.urls"
WSGI_APPLICATION = "backend.wsgi.application"
ASGI_APPLICATION = "backend.asgi.application"

# ==========================
# TEMPLATES
# ==========================
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
            ],
        },
    },
]

# ==========================
# CUSTOM COOKIE NAMES (Frontend Admin)
# ==========================
SESSION_COOKIE_NAME = "admin_session"
CSRF_COOKIE_NAME = "admin_csrftoken"

# Deployment settings (commented for local development - HTTPS only)
# SESSION_COOKIE_SECURE = True
# CSRF_COOKIE_SECURE = True

SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# ==========================
# DATABASE (Local SQLite - Deployment PostgreSQL commented)
# ==========================
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

# Deployment database config (commented for local development)
# DATABASES = {
#     "default": dj_database_url.config(
#         default=os.environ.get("DATABASE_URL"),
#         conn_max_age=600,
#         ssl_require=True,
#     )
# }

# ==========================
# CHANNELS + REDIS
# ==========================
REDIS_URL = os.environ.get("REDIS_URL")

if REDIS_URL:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels_redis.core.RedisChannelLayer",
            "CONFIG": {
                "hosts": [REDIS_URL],
            },
        }
    }
else:
    CHANNEL_LAYERS = {
        "default": {
            "BACKEND": "channels.layers.InMemoryChannelLayer",
        }
    }

# ==========================
# REST FRAMEWORK
# ==========================
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "main.authentication.CookieJWTAuthentication",
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
}

# ==========================
# SIMPLE JWT
# ==========================
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": False,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_TOKEN_CLASSES": (
        "rest_framework_simplejwt.tokens.AccessToken",
    ),
}

# ==========================
# USER MODEL
# ==========================
AUTH_USER_MODEL = "main.CustomUser"

# ==========================
# PASSWORD VALIDATION
# ==========================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ==========================
# CORS
# ==========================
CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    # Deployment origin (commented for local development)
    # "https://mvp-daroui.onrender.com",
]

CSRF_TRUSTED_ORIGINS = [
    # Deployment origin (commented for local development)
    # "https://backend-django-5ssb.onrender.com",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

# ==========================
# STATIC & MEDIA FILES
# ==========================
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

# ==========================
# LOCAL MEDIA FILES STORAGE
# ==========================
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# Cloudinary configuration (commented out - using local storage)
# cloudinary.config(
#     cloud_name=os.environ.get("CLOUDINARY_CLOUD_NAME", "dn8xzjryk"),
#     api_key=os.environ.get("CLOUDINARY_API_KEY", "911141654755575"),
#     api_secret=os.environ.get("CLOUDINARY_API_SECRET", "FCdYWgHG-bQS6ISbJ0J2aSSTkJk"),
#     secure=True  # Use HTTPS
# )

# CLOUDINARY_STORAGE = {
#     "CLOUD_NAME": os.environ.get("CLOUDINARY_CLOUD_NAME", "dn8xzjryk"),
#     "API_KEY": os.environ.get("CLOUDINARY_API_KEY", "911141654755575"),
#     "API_SECRET": os.environ.get("CLOUDINARY_API_SECRET", "FCdYWgHG-bQS6ISbJ0J2aSSTkJk"),
# }

# DEFAULT_FILE_STORAGE = "cloudinary_storage.storage.MediaCloudinaryStorage"

# ==========================
# INTERNATIONALIZATION
# ==========================
LANGUAGE_CODE = "en-us"

# Set timezone to Algeria (UTC+1)
TIME_ZONE = "Africa/Algiers"

# Enable timezone support
USE_I18N = True
USE_TZ = True

# ==========================
# DEFAULT AUTO FIELD
# ==========================
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

print(f'Active Timezone Configured: {TIME_ZONE}')
