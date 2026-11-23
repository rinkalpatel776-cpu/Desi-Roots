from django.core.exceptions import ImproperlyConfigured

from config.settings.base import *
import sentry_sdk

DEBUG = False

# ---- Secrets must come from the server's .env, never from a default ----
SECRET_KEY = env('SECRET_KEY', default='')
if len(SECRET_KEY) < 50 or SECRET_KEY.startswith('django-insecure') or 'change' in SECRET_KEY.lower():
    raise ImproperlyConfigured(
        "SECRET_KEY in .env is missing or a placeholder. Generate one with: "
        "python -c \"from django.core.management.utils import get_random_secret_key as g; print(g())\""
    )

# The admin address must be set in .env (and not be the default written in the code)
ADMIN_URL_PATH = env('ADMIN_URL_PATH', default='')
if not ADMIN_URL_PATH or ADMIN_URL_PATH == 'sp-control-pantry' or 'change-me' in ADMIN_URL_PATH:
    raise ImproperlyConfigured("Set a private ADMIN_URL_PATH in .env")

# Read allowed hosts from environment
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['desiroots.co.uk', 'www.desiroots.co.uk'])
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[f'https://{h}' for h in ALLOWED_HOSTS])

# ---- Behind Nginx ----
# Nginx handles HTTPS and passes X-Forwarded-Proto / X-Forwarded-For (see the Nginx config)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Security Headers & SSL Settings
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SESSION_COOKIE_HTTPONLY = True
# Staff admin sign-in (security review 23 Nov 2026): ends 8 hours after signing in, and when the
# browser is closed, so a lost or shared laptop doesn't stay signed in for Django's default 2 weeks.
# Visitors never get a session; this only affects staff.
SESSION_COOKIE_AGE = 8 * 60 * 60
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

# HTTP Strict Transport Security.
# Subdomains and the browser preload list are left off: email lives on Hostinger's
# servers under this domain, and preload is very hard to undo. Turn them on later if wanted.
SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=31536000)  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

# Browser content-sniffing, clickjacking and referrer protections
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
SECURE_REFERRER_POLICY = 'strict-origin-when-cross-origin'

# ---- Admin login lockout (django-axes) behind Nginx ----
# Use the visitor's real address from Nginx (one proxy in front), not Nginx's own 127.0.0.1,
# and lock out a username + address pair so a stranger can't lock every staff member out.
AXES_IPWARE_PROXY_COUNT = 1
AXES_IPWARE_META_PRECEDENCE_ORDER = ['HTTP_X_FORWARDED_FOR', 'REMOTE_ADDR']
AXES_LOCKOUT_PARAMETERS = [['username', 'ip_address']]

# ---- Error alerts by email ----
# If a page crashes (a "500" error), Django's built-in mail_admins handler emails the details
# to the business mailbox, so problems aren't first heard about from a customer.
# SERVER_EMAIL must be the real mailbox: Hostinger refuses mail "from" any other address.
ADMINS = [('Desi Roots website', NOTIFICATION_EMAIL)]
SERVER_EMAIL = DEFAULT_FROM_EMAIL
EMAIL_SUBJECT_PREFIX = '[desiroots.co.uk] '

# ---- Logging: problems go to the Gunicorn log (journalctl -u gunicorn) ----
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}, 'null': {'class': 'logging.NullHandler'}},
    'root': {'handlers': ['console'], 'level': 'WARNING'},
    'loggers': {
        # Bots visit by the server's bare IP or a fake name; Django already refuses them (400).
        # Don't email the business about each one; real crash alerts still go out.
        'django.security.DisallowedHost': {'handlers': ['null'], 'propagate': False},
    },
}

# Sentry integration (free plan: keep performance tracing low so the quota lasts)
SENTRY_DSN = env('SENTRY_DSN', default='')
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        traces_sample_rate=env.float('SENTRY_TRACES_SAMPLE_RATE', default=0.05),
        send_default_pii=False,
    )

# Public pages served from the shared cache for 10 minutes; any content change refreshes them at once
PAGE_CACHE_SECONDS = env.int('PAGE_CACHE_SECONDS', default=600)
# The cache lives outside the code folder, so a deploy never ships or wipes it
CACHES['default']['LOCATION'] = env('CACHE_DIR', default='/srv/desiroots/cache')
