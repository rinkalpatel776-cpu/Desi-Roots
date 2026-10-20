"""
Hosting on PythonAnywhere's free plan (always on, no card needed).

Differences from prod.py, because of what the free plan offers:
- MySQL instead of PostgreSQL (the free plan has no PostgreSQL). Connection details come
  from DATABASE_URL in .env, written by deploy/pythonanywhere/setup.sh.
- Outgoing email is blocked on the free plan, so enquiries are saved (see them in the admin)
  and their notification emails are only written to the server log.
- PythonAnywhere serves /static/ and /media/ itself (set up on its Web tab) and handles HTTPS.

Search engines are asked not to index the site until SITE_NOINDEX=False is set in .env,
so the temporary pythonanywhere.com address doesn't end up in Google before launch.
"""
from config.settings.base import *  # noqa: F401,F403

DEBUG = False

ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['mantra1424.pythonanywhere.com'])  # noqa: F405
CSRF_TRUSTED_ORIGINS = env.list(  # noqa: F405
    'CSRF_TRUSTED_ORIGINS', default=[f'https://{host}' for host in ALLOWED_HOSTS]
)

# PythonAnywhere terminates HTTPS and forwards this header; "Force HTTPS" is switched on in its Web tab
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# MySQL: full Unicode (product names include characters like ’) and strict mode
DATABASES['default'].setdefault('OPTIONS', {}).update({  # noqa: F405
    'charset': 'utf8mb4',
    'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
})
DATABASES['default']['CONN_MAX_AGE'] = 280  # noqa: F405  # below the free MySQL idle timeout

# The free plan blocks outgoing SMTP, so don't try to send
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# The enquiry form does not render the Turnstile widget yet
TURNSTILE_SITE_KEY = ''
TURNSTILE_SECRET_KEY = ''

if env.bool('SITE_NOINDEX', default=True):  # noqa: F405
    MIDDLEWARE = MIDDLEWARE + ['core.middleware.NoIndexMiddleware']  # noqa: F405

# Errors go to the server log (PythonAnywhere Web tab -> Log files -> error log)
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {'console': {'class': 'logging.StreamHandler'}},
    'root': {'handlers': ['console'], 'level': 'WARNING'},
}
