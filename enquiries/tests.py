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
