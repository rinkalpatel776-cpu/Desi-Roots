"""The live-server settings (config.settings.prod) refuse unsafe values and switch on HTTPS protections.

Each check imports the settings in a separate Python process, the way Gunicorn would on the server.
"""
import json
import os
import subprocess
import sys

from django.conf import settings
from django.test import SimpleTestCase

GOOD_KEY = 'k' * 20 + '9f3Lq7Zp2Rt8Vw1Xy4Bn6Mc0Hd5Js' + 'e' * 10  # 60 chars, not a placeholder
PROBE = (
    "import json, django; from django.conf import settings as s; django.setup(); "
    "print(json.dumps({k: getattr(s, k) for k in ("
    "'DEBUG', 'SECURE_SSL_REDIRECT', 'SESSION_COOKIE_SECURE', 'CSRF_COOKIE_SECURE', "
    "'SESSION_COOKIE_HTTPONLY', 'SECURE_HSTS_SECONDS', 'SECURE_CONTENT_TYPE_NOSNIFF', "
    "'X_FRAME_OPTIONS', 'ADMIN_URL_PATH', 'SECURE_HSTS_PRELOAD')}))"
)


def load_prod(**env):
    full_env = {**os.environ, 'DJANGO_SETTINGS_MODULE': 'config.settings.prod', **env}
    return subprocess.run([sys.executable, '-c', PROBE], cwd=str(settings.BASE_DIR), env=full_env,
                          capture_output=True, text=True, timeout=60)


class ProductionSettingsTests(SimpleTestCase):
    def test_refuses_to_start_with_weak_or_placeholder_secret_key(self):
        for key in ('', 'short', 'django-insecure-' + 'x' * 60, 'please-change-this-' + 'x' * 50):
            result = load_prod(SECRET_KEY=key, ADMIN_URL_PATH='private-admin-xyz')
            self.assertNotEqual(result.returncode, 0, key)
            self.assertIn('SECRET_KEY', result.stderr)

    def test_refuses_to_start_with_default_admin_address(self):
        for path in ('sp-control-pantry', 'change-me-admin'):
            result = load_prod(SECRET_KEY=GOOD_KEY, ADMIN_URL_PATH=path)
            self.assertNotEqual(result.returncode, 0, path)
            self.assertIn('ADMIN_URL_PATH', result.stderr)

    def test_safe_settings_are_switched_on(self):
        result = load_prod(SECRET_KEY=GOOD_KEY, ADMIN_URL_PATH='private-admin-xyz', SENTRY_DSN='')
        self.assertEqual(result.returncode, 0, result.stderr)
        values = json.loads(result.stdout.strip().splitlines()[-1])
        self.assertIs(values['DEBUG'], False)
        self.assertIs(values['SECURE_SSL_REDIRECT'], True)
        self.assertIs(values['SESSION_COOKIE_SECURE'], True)
        self.assertIs(values['CSRF_COOKIE_SECURE'], True)
        self.assertIs(values['SESSION_COOKIE_HTTPONLY'], True)
        self.assertGreaterEqual(values['SECURE_HSTS_SECONDS'], 31536000)
        self.assertIs(values['SECURE_HSTS_PRELOAD'], False)   # email runs on Hostinger; preload is hard to undo
        self.assertIs(values['SECURE_CONTENT_TYPE_NOSNIFF'], True)
        self.assertEqual(values['X_FRAME_OPTIONS'], 'DENY')
        self.assertNotEqual(values['ADMIN_URL_PATH'], 'admin')
