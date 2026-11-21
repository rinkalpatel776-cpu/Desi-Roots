"""Google Analytics (20 Nov 2026): off unless an ID is set, and even then the page never loads
Google's script by itself. cookie-consent.js loads it only after the visitor agrees."""
import os
import subprocess
import sys

from django.conf import settings
from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase, override_settings

GA = 'G-TEST12345'
PAGES = ['/', '/products/', '/brands/', '/about/', '/contact/', '/faq/', '/privacy/', '/cookies/', '/terms/']


@override_settings(GA_MEASUREMENT_ID="")  # whatever a local .env says
class AnalyticsOffByDefaultTests(TestCase):
    def test_no_google_code_or_cookie_settings_when_no_id_is_set(self):
        for path in PAGES:
            html = self.client.get(path).content.decode()
            self.assertNotIn('googletagmanager', html, path)
            self.assertNotIn('data-ga-id', html, path)
            self.assertNotIn('data-cookie-settings', html, path)

    def test_cookie_policy_still_says_no_analytics(self):
        response = self.client.get('/cookies/')
        self.assertContains(response, 'We do not use analytics, advertising or tracking cookies')
        self.assertNotContains(response, '_ga')


@override_settings(GA_MEASUREMENT_ID=GA)
class AnalyticsOnTests(TestCase):
    def test_every_page_offers_the_choice_but_never_loads_google_itself(self):
        for path in PAGES:
            html = self.client.get(path).content.decode()
            self.assertIn(f'data-ga-id="{GA}"', html, path)
            self.assertIn('data-cookie-settings', html, path)          # footer "Cookie settings"
            self.assertNotIn('googletagmanager.com', html, path)      # only cookie-consent.js may add it
            self.assertIn('js/cookie-consent.js', html, path)

    def test_pop_up_has_equal_accept_and_reject_and_an_analytics_switch(self):
        response = self.client.get('/')
        self.assertContains(response, 'data-cookie-choice="granted"')
        self.assertContains(response, 'data-cookie-choice="denied"')
        self.assertContains(response, 'id="cookieAnalyticsToggle"')
        self.assertContains(response, 'Google Analytics cookies')

    def test_staff_visits_are_not_counted(self):
        staff = User.objects.create_user('staff-ga', password='x-very-long-password-1', is_staff=True)
        self.client.force_login(staff)
        self.assertNotContains(self.client.get('/'), 'data-ga-id')

    def test_policies_explain_google_analytics(self):
        cookies = self.client.get('/cookies/')
        self.assertContains(cookies, '_ga')
        self.assertContains(cookies, 'only with your consent')
        self.assertContains(self.client.get('/privacy/'), 'Google Analytics')

    def test_thank_you_page_counts_a_lead(self):
        self.assertContains(self.client.get('/wholesale/thank-you/'), 'data-analytics-event="generate_lead"')

    def test_pop_up_script_is_a_file_not_inline(self):
        # Inline scripts would need a new security-policy hash on the server every time they change
        self.assertNotContains(self.client.get('/'), 'Show the privacy pop-up')


PROBE = "import django; from django.conf import settings as s; django.setup(); print(repr(s.GA_MEASUREMENT_ID))"


class AnalyticsSettingTests(SimpleTestCase):
    def load(self, value):
        env = {**os.environ, 'DJANGO_SETTINGS_MODULE': 'config.settings.dev', 'GA_MEASUREMENT_ID': value}
        result = subprocess.run([sys.executable, '-c', PROBE], cwd=str(settings.BASE_DIR), env=env,
                                capture_output=True, text=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout.strip().splitlines()[-1]

    def test_a_real_measurement_id_is_accepted(self):
        self.assertEqual(self.load(' g-ww16yg0prr '), "'G-WW16YG0PRR'")

    def test_anything_else_switches_analytics_off(self):
        for bad in ('GTM-K9HGL93R', 'UA-1234-1', '"><script>alert(1)</script>', 'G-', 'G-abc def'):
            self.assertEqual(self.load(bad), "''", bad)
