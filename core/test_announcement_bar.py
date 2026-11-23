"""Top announcement bar: one message per line in Site settings, shown in turn (18 Nov 2026)."""
from pathlib import Path

from django.conf import settings
from django.test import TestCase

from core.models import SiteSettings

SLOGAN = 'WE SUPPLY THE SPICE, YOU CREATE THE MAGIC.'
DELIVERY = ('We provide delivery services across the South West of England, including areas such as '
            'Bristol, Bath, Gloucestershire, Somerset and Cardiff.')


class AnnouncementBarTests(TestCase):
    def set_bar(self, text):
        s = SiteSettings.objects.first() or SiteSettings()
        s.announcement_bar = text
        s.save()

    def bar_html(self):
        html = self.client.get('/').content.decode()
        start = html.find('class="announcement-bar"')
        return html, (html[start:html.index('</div>', html.index('</div>', start) + 1)] if start != -1 else '')

    def test_messages_are_the_non_empty_lines_in_order(self):
        s = SiteSettings(announcement_bar=f'  {SLOGAN}  \r\n\r\n{DELIVERY}\n')
        self.assertEqual(s.announcement_messages, [SLOGAN, DELIVERY])
        self.assertEqual(SiteSettings(announcement_bar='').announcement_messages, [])

    def test_long_messages_fit_in_the_setting(self):
        self.set_bar('\n'.join([SLOGAN, DELIVERY, 'x' * 400]))
        self.assertEqual(len(SiteSettings.objects.first().announcement_messages), 3)

    def test_two_messages_rotate_with_only_the_first_showing(self):
        self.set_bar(f'{SLOGAN}\n{DELIVERY}')
        html, bar = self.bar_html()
        self.assertIn('data-rotate', bar)
        self.assertIn(f'<p class="announcement-msg is-active">{SLOGAN}</p>', bar)
        self.assertIn(f'<p class="announcement-msg" aria-hidden="true">{DELIVERY}</p>', bar)
        self.assertIn('/static/js/announcement-bar.js?v=2', html)

    def test_one_message_does_not_rotate(self):
        self.set_bar(SLOGAN)
        _, bar = self.bar_html()
        self.assertIn(SLOGAN, bar)
        self.assertNotIn('data-rotate', bar)

    def test_empty_setting_hides_the_bar(self):
        self.set_bar('')
        html, _ = self.bar_html()
        self.assertNotIn('class="announcement-bar"', html)

    def test_messages_are_escaped(self):
        self.set_bar('<script>alert(1)</script>\nSafe')
        html, bar = self.bar_html()
        self.assertNotIn('<script>alert(1)</script>', html)
        self.assertIn('&lt;script&gt;', bar)

    def test_messages_slide_like_the_hero(self):
        root = Path(settings.BASE_DIR) / 'static'
        css = (root / 'css' / 'style.css').read_text()
        hero = (root / 'css' / 'home-hero.css').read_text()
        easing = 'cubic-bezier(0.77, 0, 0.175, 1)'
        self.assertIn(f'transform .5s {easing}', hero)                       # the hero's movement
        bar = css[css.index('.announcement-track {'):css.index('Custom Sticky Navigation')]
        self.assertIn(f'transform .5s {easing}', bar)                        # the same movement in the top bar
        self.assertIn('.announcement-msg.is-leaving { transform: translateX(-100%)', bar)
        self.assertIn('overflow: hidden', bar)

    def test_script_changes_every_5_seconds_and_respects_reduced_motion(self):
        js = (Path(settings.BASE_DIR) / 'static' / 'js' / 'announcement-bar.js').read_text()
        self.assertIn('5000', js)
        self.assertIn('prefers-reduced-motion', js)
