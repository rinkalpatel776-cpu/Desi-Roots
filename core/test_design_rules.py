"""Design details from the Emil Kowalski skills audit (19 Nov 2026), so they don't slip back."""
import re
from pathlib import Path

from django.conf import settings
from django.test import TestCase

CSS = [Path(settings.BASE_DIR) / 'static' / 'css' / name for name in ('style.css', 'home-hero.css')]


class DesignRuleTests(TestCase):
    def css(self):
        return '\n'.join(p.read_text() for p in CSS)

    def test_no_transition_all(self):
        self.assertIsNone(re.search(r'transition\s*:\s*all\b', self.css()), 'name the properties instead of "all"')

    def test_no_ease_in_and_no_slow_hover_effects(self):
        css = self.css()
        self.assertIsNone(re.search(r'\bease-in\b(?!-out)', css), 'ease-in feels sluggish on UI')
        # Everyday effects stay at or under 0.3s; only the hero slide (0.5s) and top-bar fade (0.6s) are longer
        for value, unit in re.findall(r'transition[^;]*?(\d*\.?\d+)(m?s)\b', css):
            seconds = float(value) / (1000 if unit == 'ms' else 1)
            if seconds > 0.3:
                self.assertIn(seconds, (0.5, 0.6), f'{value}{unit} transition is too slow for a hover effect')

    def test_every_hover_rule_is_for_mouse_users_only(self):
        for path in CSS:
            css = re.sub(r'/\*.*?\*/', '', path.read_text(), flags=re.S)
            depth, start = 0, 0
            for i, ch in enumerate(css):
                if ch == '{':
                    if depth == 0:
                        selector = css[start:i].strip()
                        if ':hover' in selector and not selector.startswith('@'):
                            self.fail(f'{path.name}: "{selector[:60]}" hover rule not inside a (hover: hover) media query')
                    depth += 1
                elif ch == '}':
                    depth -= 1
                    if depth == 0:
                        start = i + 1

    def test_phone_bar_colour_and_reading_width(self):
        html = self.client.get('/').content.decode()
        self.assertIn('<meta name="theme-color" content="#7A3E1D">', html)
        for page in ('/about/', '/privacy/', '/cookies/', '/terms/'):
            self.assertRegex(self.client.get(page).content.decode(), r'sp-prose', page)
