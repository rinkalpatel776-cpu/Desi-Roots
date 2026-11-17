"""Visitor privacy (no Google Fonts) and a guard against running an unpatched Django (18 Nov 2026)."""
import re
from pathlib import Path

import django
from django.conf import settings
from django.test import TestCase

PAGES = ['/', '/products/', '/brands/', '/about/', '/contact/', '/faq/', '/privacy/', '/cookies/', '/terms/',
         '/wholesale/thank-you/']


class SelfHostedFontTests(TestCase):
    def test_no_page_loads_anything_from_google(self):
        for path in PAGES:
            html = self.client.get(path).content.decode()
            self.assertNotRegex(html, r'fonts\.(googleapis|gstatic)\.com', path)
            self.assertIn('/static/css/fonts.css', html, path)

    def test_error_and_lockout_pages_do_not_use_google_fonts_either(self):
        for name in ('400.html', '403_csrf.html', '500.html', 'lockout.html'):
            text = (Path(settings.BASE_DIR) / 'templates' / name).read_text()
            self.assertNotIn('fonts.googleapis.com', text, name)
            self.assertIn("css/fonts.css", text, name)

    def test_every_font_file_named_in_the_stylesheet_exists(self):
        static = Path(settings.BASE_DIR) / 'static'
        css = (static / 'css' / 'fonts.css').read_text()
        files = re.findall(r'url\(\.\./fonts/([\w.-]+\.woff2)\)', css)
        self.assertGreaterEqual(len(set(files)), 2)
        for name in set(files):
            data = (static / 'fonts' / name).read_bytes()
            self.assertEqual(data[:4], b'wOF2', name)
        self.assertIn("font-family: 'Poppins'", css)
        self.assertIn("font-family: 'Inter'", css)
        self.assertTrue((static / 'fonts' / 'OFL.txt').exists(), 'font licence file missing')


class DjangoVersionTests(TestCase):
    def test_django_has_the_november_2026_security_fixes(self):
        # 5.2.18 (Oct 2026) and 5.2.19 (Nov 2026) fixed request-header and upload denial-of-service bugs
        self.assertGreaterEqual(django.VERSION[:3], (5, 2, 19))

    def test_lock_file_pins_the_patched_django(self):
        lock = (Path(settings.BASE_DIR) / 'requirements.lock.txt').read_text()
        self.assertRegex(lock, r'(?m)^Django==5\.2\.(19|[2-9]\d)$')
