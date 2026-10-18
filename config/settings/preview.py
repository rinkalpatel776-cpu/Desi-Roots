"""
Temporary preview: share the site from this Mac through an ngrok link.

Safe to show to people: debug is off (errors show a plain page, no settings or
URL list), only ngrok hosts are accepted, cookies are HTTPS-only, admin login
lockout stays on, and search engines are told not to index it.

Not for real customers: enquiry emails only print to the terminal, and photos are
served by Django itself. Use config.settings.prod on a real server for that.

Run:  python manage.py runserver 127.0.0.1:8001 --settings=config.settings.preview
"""
from config.settings.base import *  # noqa: F401,F403

DEBUG = False

ALLOWED_HOSTS = ['.ngrok-free.app', '.ngrok-free.dev', '.ngrok.app', '.ngrok.io', 'localhost', '127.0.0.1']
CSRF_TRUSTED_ORIGINS = [
    'https://*.ngrok-free.app',
    'https://*.ngrok-free.dev',
    'https://*.ngrok.app',
    'https://*.ngrok.io',
]

# ngrok terminates HTTPS and forwards plain HTTP with this header
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Enquiries are saved to the database; their emails are printed to the terminal, not sent
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# The enquiry form does not render the Turnstile widget yet, so leave verification off here
TURNSTILE_SITE_KEY = ''
TURNSTILE_SECRET_KEY = ''

# Product photos are served by Django in this mode only (see config/urls.py)
PREVIEW_SERVE_MEDIA = True


class NoIndexMiddleware:
    """Ask search engines not to index the temporary preview."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        response['X-Robots-Tag'] = 'noindex, nofollow'
        return response


MIDDLEWARE = MIDDLEWARE + ['config.settings.preview.NoIndexMiddleware']  # noqa: F405
