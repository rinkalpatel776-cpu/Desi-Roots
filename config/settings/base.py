import os
import re
from pathlib import Path
import environ

# Initialize environ
env = environ.Env()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
# settings/base.py is 3 levels deep from root
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Read .env file if it exists
environ.Env.read_env(os.path.join(BASE_DIR, '.env'))

# Quick-start development settings - unsuitable for production
SECRET_KEY = env('SECRET_KEY', default='django-insecure-fallback-secret-key-change-in-production')

DEBUG = env.bool('DEBUG', default=False)

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=[])

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sitemaps',

    # Third party packages
    'import_export',
    'crispy_forms',
    'crispy_bootstrap5',
    'axes',
    'django_cleanup.apps.CleanupConfig',

    # Local apps
    'core.apps.CoreConfig',
    'catalogue.apps.CatalogueConfig',
    'enquiries.apps.EnquiriesConfig',
    'pages.apps.PagesConfig',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',  # Static files helper
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'axes.middleware.AxesMiddleware',  # Axes lockout middleware
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                # Core custom context processor for settings
                'core.context_processors.site_settings',
                'core.context_processors.footer_categories',
                'core.context_processors.analytics',
                'core.context_processors.has_faqs',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'

# Database
# https://docs.djangoproject.com/en/5.2/ref/settings/#databases
DATABASES = {
    'default': env.db('DATABASE_URL')
}

# Password validation
# https://docs.djangoproject.com/en/5.2/ref/settings/#auth-password-validators
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTHENTICATION_BACKENDS = [
    'axes.backends.AxesBackend',  # Keep django-axes backend
    'django.contrib.auth.backends.ModelBackend',
]

# Internationalization
# https://docs.djangoproject.com/en/5.2/topics/i18n/
LANGUAGE_CODE = 'en-gb'
TIME_ZONE = 'Europe/London'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [BASE_DIR / 'static']

# File storage. Django 4.2+ reads STORAGES (the old STATICFILES_STORAGE setting is ignored).
# Plain names here (development and tests); prod.py switches static files to content-hashed names.
STORAGES = {
    'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}

# Media files (Product photos, etc.)
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = 'bootstrap5'
CRISPY_TEMPLATE_PACK = 'bootstrap5'

# Django Axes settings
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # 1 hour cooloff
AXES_LOCKOUT_TEMPLATE = 'lockout.html'

# Admin custom URL path
ADMIN_URL_PATH = env('ADMIN_URL_PATH', default='sp-control-pantry')

# Email Backend Settings
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# Sent through the business's own Hostinger Mail box, so the domain's email (MX/SPF) records stay unchanged
EMAIL_HOST = env('EMAIL_HOST', default='smtp.hostinger.com')
EMAIL_PORT = env.int('EMAIL_PORT', default=465)
EMAIL_USE_SSL = True
EMAIL_TIMEOUT = 15  # don't keep a visitor waiting if the mail server is slow
EMAIL_HOST_USER = env('EMAIL_HOST_USER', default='support@desiroots.co.uk')
EMAIL_HOST_PASSWORD = env('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL = env('DEFAULT_FROM_EMAIL', default='support@desiroots.co.uk')
NOTIFICATION_EMAIL = env('NOTIFICATION_EMAIL', default='support@desiroots.co.uk')

# Cloudflare Turnstile Settings
TURNSTILE_SITE_KEY = env('TURNSTILE_SITE_KEY', default='')
TURNSTILE_SECRET_KEY = env('TURNSTILE_SECRET_KEY', default='')

# Google Analytics 4 (added 20 Nov 2026). Empty = off. Only loads in a visitor's browser after
# they press Accept in the cookie pop-up; never for signed-in staff. Anything that is not a
# G-XXXX measurement ID is ignored.
GA_MEASUREMENT_ID = env('GA_MEASUREMENT_ID', default='').strip().upper()
if not re.fullmatch(r'G-[A-Z0-9]{4,15}', GA_MEASUREMENT_ID):
    GA_MEASUREMENT_ID = ''


# Shared file cache (20 Nov 2026): one cache for all Gunicorn workers, so enquiry
# limits are exact and the page cache refreshes everywhere the moment content changes.
# Built into Django, free, kept on the server's own disk (no Redis or paid service).
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache',
        'LOCATION': env('CACHE_DIR', default=str(BASE_DIR / '.cache')),
        'TIMEOUT': 600,
        'OPTIONS': {'MAX_ENTRIES': 3000},
    }
}
# Whole public pages are cached this many seconds (0 = off). Off in development and tests.
PAGE_CACHE_SECONDS = 0
