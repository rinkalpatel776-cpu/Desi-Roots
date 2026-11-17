import json
import time
from unittest import mock

from django.core import mail, signing
from django.core.cache import cache
from django.test import TestCase, Client, override_settings
from .models import Enquiry
from catalogue.models import Category, Product


def started(seconds_ago=10):
    """The signed 'form shown at' value a real browser would send back."""
    return signing.dumps(int(time.time()) - seconds_ago, salt='enquiry-form')

@override_settings(TURNSTILE_SECRET_KEY='', TURNSTILE_SITE_KEY='')
class EnquiryTests(TestCase):
    def setUp(self):
        self.client = Client()
        cache.clear()
        
        # Setup mock category and product
        self.category = Category.objects.create(name="Spices", slug="spices")
        self.product = Product.objects.create(
            name="Turmeric Powder",
            slug="turmeric-powder",
            sku="SP-SPICE-101",
            category=self.category,
            is_published=True
        )

    def test_contact_page_shows_enquiry_form_without_removed_fields(self):
        response = self.client.get('/contact/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Send Message')
        for removed in ('business_type', 'category_interest', 'name="product"'):
            self.assertNotContains(response, removed)

    def test_product_link_prefills_message_on_contact_page(self):
        response = self.client.get(f'/contact/?product_id={self.product.id}')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'wholesale pricing and availability for Turmeric Powder')

    def test_old_wholesale_url_redirects_permanently_to_contact(self):
        response = self.client.get('/wholesale/')
        self.assertRedirects(response, '/contact/', status_code=301)
        response = self.client.get(f'/wholesale/?product_id={self.product.id}')
        self.assertRedirects(response, f'/contact/?product_id={self.product.id}', status_code=301)

    def test_post_to_old_wholesale_url_still_saves(self):
        payload = {
            'name': 'Old Tab', 'email': 'old@tab.co.uk', 'phone': '0117 000 0000',
            'message': 'Sent from a page opened before the change.', 'consent_given': 'on', 'website': '',
            'form_started': started(),
        }
        response = self.client.post('/wholesale/', data=payload)
        self.assertRedirects(response, '/wholesale/thank-you/')
        self.assertEqual(Enquiry.objects.count(), 1)

    def test_valid_enquiry_submission(self):
        # Submit a valid enquiry
        payload = {
            'name': 'John Doe',
            'business_name': 'Bristol Curry House',
            'email': 'john@curryhouse.co.uk',
            'phone': '0117 999 9999',
            'message': 'We need 50kg of turmeric powder weekly. Please quote.',
            'consent_given': 'on', # Checkbox is sent as 'on'
            'website': '', # Leave honeypot empty
            'form_started': started(),
        }
        
        # Submit POST request
        response = self.client.post('/contact/', data=payload)
        
        # Verify redirect to thank you page
        self.assertRedirects(response, '/wholesale/thank-you/')
        
        # Check database records
        self.assertEqual(Enquiry.objects.count(), 1)
        enquiry = Enquiry.objects.first()
        self.assertEqual(enquiry.name, 'John Doe')
        self.assertEqual(enquiry.business_name, 'Bristol Curry House')
        self.assertEqual(enquiry.status, 'new')

    def test_honeypot_spam_prevention(self):
        # Submit form with honeypot field filled
        payload = {
            'name': 'Spam Bot',
            'business_name': 'Spam Co',
            'email': 'spam@bot.com',
            'phone': '07000000000',
            'message': 'Spam message',
            'consent_given': 'on',
            'website': 'http://spambot.com', # Honeypot field filled
            'form_started': started(),
        }

        response = self.client.post('/contact/', data=payload)

        # Bots are quietly shown the thank-you page, but nothing is saved or emailed
        self.assertRedirects(response, '/wholesale/thank-you/')
        self.assertEqual(Enquiry.objects.count(), 0)
        self.assertEqual(len(mail.outbox), 0)

    def test_missing_required_fields(self):
        # Submit form with missing name
        payload = {
            'name': '',
            'business_name': 'Bristol Curry House',
            'email': 'john@curryhouse.co.uk',
            'phone': '0117 999 9999',
            'message': 'Catering needs...',
            'consent_given': 'on'
        }
        
        response = self.client.post('/contact/', data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, 'pages/contact.html')
        self.assertFormError(response.context['form'], 'name', "This field is required.")
        self.assertEqual(Enquiry.objects.count(), 0)


def good_payload(**extra):
    data = {
        'name': 'Asha Patel', 'business_name': 'Asha Kitchen', 'email': 'asha@kitchen.co.uk',
        'phone': '0117 123 4567', 'message': 'Please quote for 20kg basmati rice.',
        'consent_given': 'on', 'website': '', 'form_started': started(),
    }
    data.update(extra)
    return data


@override_settings(TURNSTILE_SECRET_KEY='', TURNSTILE_SITE_KEY='')
class EnquirySecurityTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_no_turnstile_widget_without_keys(self):
        response = self.client.get('/contact/')
        self.assertNotContains(response, 'cf-turnstile')

    def test_message_longer_than_limit_is_rejected(self):
        response = self.client.post('/contact/', data=good_payload(message='x' * 5001))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Enquiry.objects.count(), 0)

    def test_auto_reply_is_limited_per_visitor(self):
        for i in range(5):
            self.client.post('/contact/', data=good_payload(email=f'person{i}@example.co.uk'))
        self.assertEqual(Enquiry.objects.count(), 5)              # every enquiry is still saved
        replies = [m for m in mail.outbox if m.subject.startswith('Enquiry Received')]
        self.assertEqual(len(replies), 3)                          # but only 3 auto-replies per hour


@override_settings(TURNSTILE_SECRET_KEY='', TURNSTILE_SITE_KEY='', NOTIFICATION_EMAIL='support@example.com')
class EnquiryAttackTests(TestCase):
    """Found in the attack pass (17 Nov 2026) and fixed."""

    def setUp(self):
        cache.clear()

    def test_line_breaks_in_names_cannot_add_email_headers_or_hide_the_enquiry(self):
        self.client.post('/contact/', data=good_payload(business_name='Evil\r\nBcc: victim@example.com',
                                                        name='Asha\nPatel', phone='0117\t496 0000'))
        enquiry = Enquiry.objects.get()
        self.assertEqual(enquiry.business_name, 'Evil Bcc: victim@example.com')
        self.assertEqual(enquiry.name, 'Asha Patel')
        self.assertEqual(enquiry.phone, '0117 496 0000')
        to_business = [m for m in mail.outbox if m.to == ['support@example.com']]
        self.assertEqual(len(to_business), 1)            # the owner is still told about it
        self.assertEqual(to_business[0].bcc, [])
        self.assertNotIn('\n', to_business[0].subject)

    def test_one_visitor_cannot_flood_enquiries(self):
        from enquiries.views import ENQUIRY_LIMIT_PER_HOUR
        for i in range(ENQUIRY_LIMIT_PER_HOUR + 3):
            response = self.client.post('/contact/', data=good_payload(email=f'flood{i}@example.co.uk'))
        self.assertEqual(Enquiry.objects.count(), ENQUIRY_LIMIT_PER_HOUR)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'several enquiries in the last hour')
        to_business = [m for m in mail.outbox if m.to == ['support@example.com']]
        self.assertEqual(len(to_business), ENQUIRY_LIMIT_PER_HOUR)
        # A different visitor is not affected
        self.client.post('/contact/', data=good_payload(email='other@example.co.uk'), REMOTE_ADDR='203.0.113.9')
        self.assertTrue(Enquiry.objects.filter(email='other@example.co.uk').exists())

    def test_old_form_must_be_sent_again(self):
        response = self.client.post('/contact/', data=good_payload(form_started=started(seconds_ago=2 * 24 * 3600)))
        self.assertEqual(Enquiry.objects.count(), 0)
        self.assertContains(response, 'open for a long time')
        # The re-shown form carries a fresh token, so sending it again works
        import re
        token = re.search(r'name="form_started" value="([^"]+)"', response.content.decode()).group(1)
        import time as _t
        from unittest import mock
        with mock.patch('enquiries.forms.time.time', return_value=_t.time() + 10):
            self.client.post('/contact/', data=good_payload(form_started=token))
        self.assertEqual(Enquiry.objects.count(), 1)


@override_settings(TURNSTILE_SECRET_KEY='', TURNSTILE_SITE_KEY='', NOTIFICATION_EMAIL='support@example.com')
class EnquiryReferenceTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_emails_carry_reference_and_reply_goes_to_customer(self):
        self.client.post('/contact/', data=good_payload(email='buyer@example.co.uk', business_name='Spice Kitchen Ltd'))
        enquiry = Enquiry.objects.get()
        ref = f'DR-{enquiry.pk}'
        self.assertEqual(enquiry.reference, ref)
        to_business = next(m for m in mail.outbox if m.to == ['support@example.com'])
        self.assertIn(ref, to_business.subject)
        self.assertIn('Spice Kitchen Ltd', to_business.subject)
        self.assertEqual(to_business.reply_to, ['buyer@example.co.uk'])
        to_customer = next(m for m in mail.outbox if m.to == ['buyer@example.co.uk'])
        self.assertIn(ref, to_customer.subject)
        self.assertIn(ref, to_customer.body)

    def test_admin_search_finds_enquiry_by_reference(self):
        from django.contrib.auth.models import User
        self.client.post('/contact/', data=good_payload())
        self.client.post('/contact/', data=good_payload(email='other@example.co.uk'))
        first = Enquiry.objects.order_by('pk').first()
        admin = User.objects.create_superuser('boss', 'boss@example.com', 'a-long-test-password-123')
        self.client.force_login(admin)
        from django.conf import settings
        response = self.client.get(f'/{settings.ADMIN_URL_PATH}/enquiries/enquiry/', {'q': f'dr-{first.pk}'})
        self.assertEqual(list(response.context['cl'].queryset), [first])


@override_settings(TURNSTILE_SECRET_KEY='secret-test', TURNSTILE_SITE_KEY='site-test')
class TurnstileTests(TestCase):
    def setUp(self):
        cache.clear()

    def _cloudflare_says(self, success):
        response = mock.MagicMock()
        response.read.return_value = json.dumps({'success': success}).encode()
        response.__enter__.return_value = response
        return mock.patch('enquiries.forms.urllib.request.urlopen', return_value=response)

    def test_widget_shown_when_keys_set(self):
        response = self.client.get('/contact/')
        self.assertContains(response, 'cf-turnstile')
        self.assertContains(response, 'challenges.cloudflare.com/turnstile')

    def test_failed_check_blocks_the_enquiry(self):
        with self._cloudflare_says(False):
            self.client.post('/contact/', data=good_payload(**{'cf-turnstile-response': 'token'}))
        self.assertEqual(Enquiry.objects.count(), 0)

    def test_passed_check_saves_the_enquiry(self):
        with self._cloudflare_says(True):
            response = self.client.post('/contact/', data=good_payload(**{'cf-turnstile-response': 'token'}))
        self.assertRedirects(response, '/wholesale/thank-you/')
        self.assertEqual(Enquiry.objects.count(), 1)


@override_settings(TURNSTILE_SECRET_KEY='', TURNSTILE_SITE_KEY='', NOTIFICATION_EMAIL='support@example.com')
class RepeatEnquiryTests(TestCase):
    """A double click, slow-internet retry or page refresh must not save or email an enquiry twice (18 Nov 2026)."""

    def setUp(self):
        cache.clear()

    def business_emails(self):
        return [m for m in mail.outbox if m.to == ['support@example.com']]

    def test_sending_the_same_enquiry_twice_saves_and_emails_once(self):
        first = self.client.post('/contact/', data=good_payload())
        second = self.client.post('/contact/', data=good_payload())
        self.assertRedirects(first, '/wholesale/thank-you/', fetch_redirect_response=False)
        self.assertRedirects(second, '/wholesale/thank-you/', fetch_redirect_response=False)  # visitor sees success
        self.assertEqual(Enquiry.objects.count(), 1)
        self.assertEqual(len(self.business_emails()), 1)
        self.assertEqual(len([m for m in mail.outbox if m.to == ['asha@kitchen.co.uk']]), 1)

    def test_same_message_with_different_capitals_or_spaces_in_email_is_still_a_repeat(self):
        self.client.post('/contact/', data=good_payload())
        self.client.post('/contact/', data=good_payload(email=' Asha@Kitchen.co.uk '))
        self.assertEqual(Enquiry.objects.count(), 1)

    def test_two_copies_arriving_at_the_same_moment_save_once(self):
        # Simulate the second copy arriving before the first is in the database
        from enquiries import views
        with mock.patch.object(views, '_already_received', return_value=False):
            self.client.post('/contact/', data=good_payload())
            self.client.post('/contact/', data=good_payload())
        self.assertEqual(Enquiry.objects.count(), 1)
        self.assertEqual(len(self.business_emails()), 1)

    def test_a_different_message_is_a_new_enquiry(self):
        self.client.post('/contact/', data=good_payload())
        self.client.post('/contact/', data=good_payload(message='Also 10 x 5 kg chapatti flour, please.'))
        self.assertEqual(Enquiry.objects.count(), 2)
        self.assertEqual(len(self.business_emails()), 2)

    def test_the_same_message_after_ten_minutes_is_accepted(self):
        from datetime import timedelta
        from django.utils import timezone
        self.client.post('/contact/', data=good_payload())
        Enquiry.objects.update(created_at=timezone.now() - timedelta(minutes=11))
        cache.clear()
        self.client.post('/contact/', data=good_payload())
        self.assertEqual(Enquiry.objects.count(), 2)

    def test_repeats_do_not_use_up_the_hourly_limit(self):
        from enquiries.views import ENQUIRY_LIMIT_PER_HOUR
        for _ in range(ENQUIRY_LIMIT_PER_HOUR + 2):
            self.client.post('/contact/', data=good_payload())          # one real + repeats
        response = self.client.post('/contact/', data=good_payload(message='A genuinely new question.'))
        self.assertRedirects(response, '/wholesale/thank-you/', fetch_redirect_response=False)
        self.assertEqual(Enquiry.objects.count(), 2)

    def test_contact_page_loads_the_send_once_script(self):
        response = self.client.get('/contact/')
        self.assertContains(response, 'data-send-once')
        self.assertContains(response, '/static/js/enquiry-form.js')
