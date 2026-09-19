from config.settings.base import *

DEBUG = True
ALLOWED_HOSTS = ['*']

# Local development specific overrides
# E.g., we can use console email backend for local testing to avoid SMTP errors:
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Disable Axes lockout checks in development to avoid lockouts during testing if preferred
AXES_ENABLED = False

# Allow CSRF POST requests through ngrok tunnels and local development
CSRF_TRUSTED_ORIGINS = [
    'https://*.ngrok-free.app',
    'https://*.ngrok-free.dev',
    'https://*.ngrok.io',
    'https://*.loca.lt',
    'https://wispy-handshake-timid.ngrok-free.dev',
    'http://localhost:8001',
    'http://127.0.0.1:8001',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]

SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
USE_X_FORWARDED_HOST = True

# Disable Turnstile testing widget in local development
TURNSTILE_SITE_KEY = ''
TURNSTILE_SECRET_KEY = ''


