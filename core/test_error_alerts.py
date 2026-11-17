"""A crashing page emails the details to the business mailbox (Django's built-in mail_admins).

The URL patterns below exist only inside this test (ROOT_URLCONF is pointed here), so the real
site never has a "crash" page.
"""
from django.core import mail
from django.http import HttpResponse
from django.test import TestCase, override_settings
from django.urls import path


def crash(request):
    raise RuntimeError('Test crash for the error alert')


def fine(request):
    return HttpResponse('ok')


urlpatterns = [path('crash/', crash), path('fine/', fine)]

ALERT_SETTINGS = dict(
    ROOT_URLCONF='core.test_error_alerts', DEBUG=False,
    ADMINS=[('Desi Roots website', 'support@desiroots.co.uk')],
    SERVER_EMAIL='support@desiroots.co.uk', EMAIL_SUBJECT_PREFIX='[desiroots.co.uk] ',
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
)


@override_settings(**ALERT_SETTINGS)
class ErrorAlertTests(TestCase):
    def setUp(self):
        self.client.raise_request_exception = False

    def test_a_crash_emails_the_business(self):
        response = self.client.get('/crash/')
        self.assertEqual(response.status_code, 500)
        self.assertEqual(len(mail.outbox), 1)
        alert = mail.outbox[0]
        self.assertEqual(alert.to, ['support@desiroots.co.uk'])
        self.assertEqual(alert.from_email, 'support@desiroots.co.uk')
        self.assertTrue(alert.subject.startswith('[desiroots.co.uk] '))
        self.assertIn('Test crash for the error alert', alert.body)

    def test_normal_pages_and_404s_send_no_email(self):
        self.client.get('/fine/')
        self.client.get('/no-such-page/')
        self.assertEqual(len(mail.outbox), 0)
