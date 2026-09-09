"""
Django settings for AI Employee Operations Platform (WorkFlow AI).
"""

from pathlib import Path
from datetime import timedelta
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

DEBUG = config('DEBUG', default=True, cast=bool)
SECRET_KEY = config('SECRET_KEY', default='django-insecure-dev-key-change-me')
if not DEBUG and SECRET_KEY == 'django-insecure-dev-key-change-me':
    raise RuntimeError('SECRET_KEY must be set to a strong value when DEBUG=False.')
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1', cast=Csv())

INSTALLED_APPS = [
    'daphne',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'corsheaders',

    'accounts',
    'company',
    'attendance',
    'channels',
    'teams',
    'workspace',
    'leave',
    'ai',
    'notifications',
    'payroll',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# --- Database ---
# DB_ENGINE selects the backend: 'sqlite' (easy local development) or
# 'postgresql' (production target). All
# PostgreSQL credentials come from environment variables; nothing is
# hard-coded, and no secret defaults to a real-looking value.
DB_ENGINE = config('DB_ENGINE', default='sqlite').lower()

if DB_ENGINE == 'sqlite':
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / config('SQLITE_NAME', default='db.sqlite3'),
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': config('DB_NAME', default='ai_ops_platform'),
            'USER': config('DB_USER', default='postgres'),
            'PASSWORD': config('DB_PASSWORD', default=''),
            'HOST': config('DB_HOST', default='localhost'),
            'PORT': config('DB_PORT', default='5432'),
        }
    }

AUTH_USER_MODEL = 'accounts.User'

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = 'media/'
MEDIA_ROOT = BASE_DIR / 'media'

# --- Upload limits (defense against oversized/abusive uploads) ---
DATA_UPLOAD_MAX_MEMORY_SIZE = config('MAX_UPLOAD_SIZE_MB', default=10, cast=int) * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = DATA_UPLOAD_MAX_MEMORY_SIZE

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# --- DRF ---
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'core.authentication.ActiveUserJWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'EXCEPTION_HANDLER': 'core.exception_handler.custom_exception_handler',
}

# --- JWT ---
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=config('ACCESS_TOKEN_LIFETIME_MINUTES', default=15, cast=int)),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=config('REFRESH_TOKEN_LIFETIME_DAYS', default=7, cast=int)),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# --- CORS ---
CORS_ALLOWED_ORIGINS = config('CORS_ALLOWED_ORIGINS', default='http://localhost:5173', cast=Csv())

# --- CSRF ---
# Only relevant for Django's own session/admin forms (the API itself is
# JWT-authenticated, stateless, and CSRF-exempt by nature - DRF's
# SessionAuthentication is not in DEFAULT_AUTHENTICATION_CLASSES above).
CSRF_TRUSTED_ORIGINS = config('CSRF_TRUSTED_ORIGINS', default='http://localhost:5173', cast=Csv())

# --- Production security toggles ---
# All default to safe-for-local-dev (off) and only activate when
# explicitly enabled via env for a real deployment - never force these
# on, since that would break local HTTP development.
SECURE_SSL_REDIRECT = config('SECURE_SSL_REDIRECT', default=False, cast=bool)
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=False, cast=bool)
CSRF_COOKIE_SECURE = config('CSRF_COOKIE_SECURE', default=False, cast=bool)
SECURE_HSTS_SECONDS = config('SECURE_HSTS_SECONDS', default=0, cast=int)
SECURE_HSTS_INCLUDE_SUBDOMAINS = config('SECURE_HSTS_INCLUDE_SUBDOMAINS', default=False, cast=bool)
SECURE_HSTS_PRELOAD = config('SECURE_HSTS_PRELOAD', default=False, cast=bool)
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# --- Email (console backend for local dev; no OTP/verification flows per scope) ---
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_USE_SSL = config('EMAIL_USE_SSL', default=False, cast=bool)
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@company.local')

# --- Channels ---
ASGI_APPLICATION = 'config.asgi.application'

REDIS_URL = config('REDIS_URL', default='redis://localhost:6379/0')
USE_REDIS_CHANNEL_LAYER = config('USE_REDIS_CHANNEL_LAYER', default=False, cast=bool)

if USE_REDIS_CHANNEL_LAYER:
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels_redis.core.RedisChannelLayer',
            'CONFIG': {
                'hosts': [REDIS_URL],
            },
        }
    }
else:
    # In-memory layer - single-process only, fine for local dev/testing
    # without a running Redis instance. Set USE_REDIS_CHANNEL_LAYER=True
    # once Redis is available (required for multi-worker deployments).
    CHANNEL_LAYERS = {
        'default': {
            'BACKEND': 'channels.layers.InMemoryChannelLayer',
        }
    }

# --- Groq AI ---
GROQ_API_KEY = config('GROQ_API_KEY', default='')
GROQ_MODEL = config('GROQ_MODEL', default='openai/gpt-oss-120b')

# --- Celery ---
CELERY_BROKER_URL = config('CELERY_BROKER_URL', default=REDIS_URL)
CELERY_RESULT_BACKEND = config('CELERY_RESULT_BACKEND', default=REDIS_URL)
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# --- AI observability ---
AI_OBSERVABILITY_ENABLED = config('AI_OBSERVABILITY_ENABLED', default=True, cast=bool)
AI_LOG_LEVEL = config('AI_LOG_LEVEL', default='INFO')
AI_SEMANTIC_RETRIEVAL_ENABLED = config('AI_SEMANTIC_RETRIEVAL_ENABLED', default=False, cast=bool)
AI_SEMANTIC_MODEL = config('AI_SEMANTIC_MODEL', default='all-MiniLM-L6-v2')
REALTIME_COMPANY_BROADCAST_MAX_USERS = config('REALTIME_COMPANY_BROADCAST_MAX_USERS', default=2000, cast=int)


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'workflow_ai': {
            'format': '[%(asctime)s] %(levelname)s %(name)s %(message)s',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'workflow_ai',
        },
    },
    'loggers': {
        'workflow_ai.ai': {
            'handlers': ['console'],
            'level': AI_LOG_LEVEL,
            'propagate': False,
        },
    },
}

# --- Automation windows (configurable, sensible defaults per architecture.md) ---
TASK_REMINDER_WINDOW_HOURS = config('TASK_REMINDER_WINDOW_HOURS', default=24, cast=int)
ISSUE_ESCALATION_HOURS = config('ISSUE_ESCALATION_HOURS', default=24, cast=int)
