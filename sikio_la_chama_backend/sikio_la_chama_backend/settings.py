"""
Django settings for sikio_la_chama_backend project.
"""

from pathlib import Path
from decouple import config
import os
import dj_database_url

# -------------------------------
# Base Directory
# -------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent

# -------------------------------
# Security
# -------------------------------
SECRET_KEY = config('SECRET_KEY', default='unsafe-secret-key')
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config(
    'ALLOWED_HOSTS',
    default='127.0.0.1,localhost',
    cast=lambda v: [s.strip() for s in v.split(',')]
)

# -------------------------------
# Installed Applications
# -------------------------------
INSTALLED_APPS = [
    # Django default apps
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    'django_filters',
    'django_extensions',
    'cloudinary',
    'cloudinary_storage',

    # Project apps
    'users.apps.UsersConfig',
    'user_messages.apps.UserMessagesConfig',
    'polls.apps.PollsConfig',
    'reports.apps.ReportsConfig',
    'feeds.apps.FeedsConfig',
    'institutions.apps.InstitutionsConfig',
    'leaders.apps.LeadersConfig',
    'analytics.apps.AnalyticsConfig',
    'problem_types.apps.ProblemTypesConfig',
    'announcements.apps.AnnouncementsConfig',
    'ilani.apps.IlaniConfig',
]

# -------------------------------
# Middleware
# -------------------------------
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # WhiteNoise for static files
    'django.contrib.sessions.middleware.SessionMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # must be above CommonMiddleware
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# -------------------------------
# Root URL configuration
# -------------------------------
ROOT_URLCONF = 'sikio_la_chama_backend.urls'

# -------------------------------
# Templates
# -------------------------------
TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

# -------------------------------
# Logging
# -------------------------------
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'loggers': {'django': {'handlers': ['console'], 'level': 'DEBUG'}},
}

# -------------------------------
# WSGI
# -------------------------------
WSGI_APPLICATION = 'sikio_la_chama_backend.wsgi.application'

# -------------------------------
# Database (PostgreSQL on Render)
# -------------------------------
DATABASES = {
    'default': dj_database_url.config(
        default=config('DATABASE_URL')
    )
}

# -------------------------------
# Password validation
# -------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

# -------------------------------
# Internationalization
# -------------------------------
LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'Africa/Dar_es_Salaam'
USE_I18N = True
USE_TZ = True

# -------------------------------
# Static files (WhiteNoise)
# -------------------------------
STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# -------------------------------
# Cloudinary Media Storage
# -------------------------------
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'

CLOUDINARY_STORAGE = {
    'CLOUD_NAME': config('CLOUDINARY_CLOUD_NAME'),
    'API_KEY': config('CLOUDINARY_API_KEY'),
    'API_SECRET': config('CLOUDINARY_API_SECRET'),
}

MEDIA_URL = '/media/'  # Cloudinary serves media, local MEDIA_ROOT not needed

# -------------------------------
# Default primary key field type
# -------------------------------
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# -------------------------------
# REST Framework
# -------------------------------
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.BasicAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
    'DEFAULT_FILTER_BACKENDS': ['django_filters.rest_framework.DjangoFilterBackend'],
}

# -------------------------------
# CORS (for Flutter / web apps)
# -------------------------------
CORS_ALLOWED_ORIGINS = [
    "http://localhost:8081",
    "http://127.0.0.1:8081",
    "http://10.0.2.2:8000",
    "http://192.168.1.191:8000",
    "sikio-la-chama-backend.onrender.com"
    # Add your frontend production URL
    # "https://yourfrontend.com",
]

# -------------------------------
# MapTiler API key
# -------------------------------
MAPTILER_API_KEY = config('MAPTILER_API_KEY', default='qu2ntYeE6GTsvZvPY9PF')

# -------------------------------
# Security for production
# -------------------------------
SECURE_SSL_REDIRECT = not DEBUG
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True

# -------------------------------
# Custom user model
# -------------------------------
AUTH_USER_MODEL = 'users.User'
