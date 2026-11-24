"""Hashed static file names for long browser caching (24 Nov 2026)."""
import re
import shutil
import tempfile
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase, override_settings

HASHED = {**settings.STORAGES, 'staticfiles': {'BACKEND': 'core.storage.DesiRootsStaticStorage'}}


class HashedStaticFilesTests(TestCase):
    """Runs collectstatic with the live server's storage into a temporary folder."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.root = tempfile.mkdtemp(prefix='dr-static-test-')
        with override_settings(STATIC_ROOT=cls.root, STORAGES=HASHED):
            call_command('collectstatic', interactive=False, verbosity=0, stdout=StringIO())

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.root, ignore_errors=True)
        super().tearDownClass()

    def test_collectstatic_writes_hashed_copies_and_keeps_plain_names(self):
        root = Path(self.root)
        self.assertTrue((root / 'css' / 'style.css').exists())                # Nginx error pages and old links still work
        self.assertTrue(list((root / 'css').glob('style.*.css')))
        self.assertTrue((root / 'staticfiles.json').exists())
        self.assertTrue((root / 'errors' / 'busy.html').exists())             # Nginx's own error page keeps its name

    def test_pages_link_to_hashed_css_and_js(self):
        with override_settings(STATIC_ROOT=self.root, STORAGES=HASHED):
            html = self.client.get('/').content.decode()
        self.assertRegex(html, r'/static/css/style\.[0-9a-f]{12}\.css')
        self.assertRegex(html, r'/static/js/hero-slider\.[0-9a-f]{12}\.js|/static/js/announcement-bar\.[0-9a-f]{12}\.js')
        self.assertNotRegex(html, r'/static/css/style\.css[?"]')

    def test_a_file_missing_from_the_manifest_falls_back_instead_of_crashing(self):
        from django.templatetags.static import static
        with override_settings(STATIC_ROOT=self.root, STORAGES=HASHED):
            self.assertEqual(static('css/not-a-real-file.css'), '/static/css/not-a-real-file.css')

    def test_bootstrap_files_keep_their_integrity_hashes(self):
        import base64
        import hashlib
        import json
        manifest = json.loads((Path(self.root) / 'staticfiles.json').read_text())['paths']
        base = (Path(settings.BASE_DIR) / 'templates' / 'base.html').read_text()
        for name in ('vendor/bootstrap/bootstrap.min.css', 'vendor/bootstrap/bootstrap.bundle.min.js'):
            data = (Path(self.root) / manifest[name]).read_bytes()
            sri = 'sha384-' + base64.b64encode(hashlib.sha384(data).digest()).decode()
            self.assertIn(f'integrity="{sri}"', base, name)

    def test_icon_font_link_is_rewritten_to_its_hashed_name(self):
        import json
        manifest = json.loads((Path(self.root) / 'staticfiles.json').read_text())['paths']
        css = (Path(self.root) / manifest['vendor/bootstrap-icons/bootstrap-icons.min.css']).read_text()
        self.assertRegex(css, r'fonts/bootstrap-icons-desiroots\.[0-9a-f]{12}\.woff2')
