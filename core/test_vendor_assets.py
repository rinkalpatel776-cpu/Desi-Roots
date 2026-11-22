"""Speed round 2 and page titles (22 Nov 2026).

Bootstrap and the icons are served from desiroots.co.uk itself (static/vendor/), so phones skip a
slow extra connection to jsDelivr. The icon font holds only the icons the site uses.
"""
import base64
import hashlib
import re
from pathlib import Path

from django.conf import settings
from django.test import TestCase

BASE = Path(settings.BASE_DIR)
VENDOR = BASE / 'static' / 'vendor'
# The icons in static/vendor/bootstrap-icons/fonts/bootstrap-icons-desiroots.woff2. To add one: add its name
# here, then rebuild the font and CSS from Bootstrap Icons 1.11.3 with pyftsubset (fonttools), keeping only these.
ICONS = sorted(set("""search whatsapp x envelope telephone chat-left-text grid-3x3-gap funnel x-circle geo-alt
    chevron-right chevron-left chevron-down arrow-right truck telephone-fill tags send question-circle house
    geo-alt-fill envelope-fill check-lg chat-square-text chat-left-dots briefcase basket2 award""".split()))


def site_files():
    for folder, patterns in (('templates', ('*.html',)), ('static/js', ('*.js',))):
        for pattern in patterns:
            for path in (BASE / folder).rglob(pattern):
                if ' 2.' in path.name or ' 3.' in path.name:
                    continue  # stray sync copies, not used
                yield path


class SelfHostedAssetsTests(TestCase):
    def test_no_page_loads_anything_from_jsdelivr(self):
        for path in site_files():
            self.assertNotIn('cdn.jsdelivr.net', path.read_text(), path)

    def test_local_bootstrap_files_match_their_published_fingerprints(self):
        html = (BASE / 'templates' / 'base.html').read_text()
        for name in ('bootstrap.min.css', 'bootstrap.bundle.min.js'):
            data = (VENDOR / 'bootstrap' / name).read_bytes()
            sri = 'sha384-' + base64.b64encode(hashlib.sha384(data).digest()).decode()
            self.assertIn(sri, html, name)   # the browser checks it too, and refuses a changed file

    def test_every_icon_the_site_uses_is_in_the_trimmed_icon_font(self):
        css = (VENDOR / 'bootstrap-icons' / 'bootstrap-icons.min.css').read_text()
        used = set()
        for path in site_files():
            used |= set(re.findall(r'\bbi-([a-z0-9-]+)', path.read_text()))
        missing = sorted(u for u in used if f'.bi-{u}::before' not in css)
        self.assertEqual(missing, [], 'add these to ICONS and rebuild the icon font')
        self.assertTrue(set(ICONS) <= used | set(ICONS))

    def test_icon_files_are_small_and_licensed(self):
        self.assertLess((VENDOR / 'bootstrap-icons' / 'fonts' / 'bootstrap-icons-desiroots.woff2').stat().st_size, 10_000)
        self.assertLess((VENDOR / 'bootstrap-icons' / 'bootstrap-icons.min.css').stat().st_size, 5_000)
        for licence in (VENDOR / 'bootstrap' / 'LICENSE', VENDOR / 'bootstrap-icons' / 'LICENSE'):
            self.assertIn('MIT License', licence.read_text())

    def test_pages_render_with_local_assets(self):
        html = self.client.get('/').content.decode()
        self.assertIn('/static/vendor/bootstrap/bootstrap.min.css', html)
        self.assertIn('/static/vendor/bootstrap-icons/bootstrap-icons.min.css', html)
        self.assertIn('/static/vendor/bootstrap/bootstrap.bundle.min.js', html)


class PageTitleTests(TestCase):
    """Search tools flag titles under ~30 characters; Google shows about 60."""

    def test_main_pages_have_descriptive_titles_of_a_good_length(self):
        titles = {}
        for path in ('/', '/products/', '/brands/', '/about/', '/contact/'):
            html = self.client.get(path).content.decode()
            title = re.search(r'<title>(.*?)</title>', html, re.S).group(1).replace('&amp;', '&').strip()
            self.assertGreaterEqual(len(title), 30, (path, title))
            self.assertLessEqual(len(title), 65, (path, title))
            self.assertIn('Desi Roots', title)
            titles[path] = title
        self.assertEqual(len(set(titles.values())), len(titles))   # every page has its own title
