from config.settings.base import *
import sentry_sdk

DEBUG = False

# Read allowed hosts from environment
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['spicepantry.co.uk', 'www.spicepantry.co.uk'])

# Security Headers & SSL Settings
SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

# HTTP Strict Transport Security
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Browser XSS & content sniffing protections
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# Sentry integration
SENTRY_DSN = env('SENTRY_DSN', default='')
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        # Set traces_sample_rate to 1.0 to capture 100% of transactions for performance monitoring.
        traces_sample_rate=1.0,
        # Set profiles_sample_rate to 1.0 to profile 100% of transactions.
        profiles_sample_rate=1.0,
    )
