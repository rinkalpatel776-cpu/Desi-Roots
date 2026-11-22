"""UI states review (21 Nov 2026): busy/too-many pages, reference on thank-you, kept enquiry text,
helpful no-results, bot trap hidden from screen readers."""
import re
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.test import TestCase, override_settings

from catalogue.models import Category, Product
from enquiries.models import Enquiry
from enquiries.tests import good_payload

STATIC = Path(settings.BASE_DIR) / 'static'


class NginxErrorPageTests(TestCase):
    """static/errors/*.html are shown by Nginx itself (502/503/504 and 429), outside Django."""

    def test_pages_exist_are_plain_html_and_hold_no_contact_details(self):
        for name in ('busy.html', 'too-many.html'):
            html = (STATIC / 'errors' / name).read_text()
            self.assertIn('<title>', html, name)
            self.assertNotIn('<script', html, name)                      # the security policy allows no inline scripts
            self.assertNotRegex(html, r'@|\+44|\b0\d{3,4} ?\d{3}', name)  # contact details live in Site Settings only
            self.assertIn('/static/images/logo-160.webp', html, name)

    def test_busy_page_tries_again_by_itself(self):
        html = (STATIC / 'errors' / 'busy.html').read_text()
        self.assertIn('http-equiv="refresh" content="10"', html)


@override_settings(TURNSTILE_SECRET_KEY='', TURNSTILE_SITE_KEY='')
class ThankYouReferenceTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_thank_you_page_shows_the_new_reference_once(self):
        response = self.client.post('/contact/', data=good_payload(), follow=True)
        enquiry = Enquiry.objects.get()
        self.assertContains(response, f'Your reference is <strong>{enquiry.reference}</strong>', html=False)
        self.assertNotContains(self.client.get('/wholesale/thank-you/'), 'Your reference is')  # shown once

    def test_bots_get_no_reference(self):
        response = self.client.post('/contact/', data=good_payload(website='http://spam.example'), follow=True)
        self.assertEqual(Enquiry.objects.count(), 0)
        self.assertNotContains(response, 'Your reference is')

    def test_thank_you_page_clears_the_kept_enquiry_text(self):
        html = self.client.get('/wholesale/thank-you/').content.decode()
        self.assertIn('data-enquiry-sent', html)
        self.assertIn('js/enquiry-draft.js', html)


class KeptEnquiryTextTests(TestCase):
    def test_contact_form_keeps_unsent_text(self):
        html = self.client.get('/contact/').content.decode()
        self.assertIn('data-enquiry-draft', html)
        self.assertIn('js/enquiry-draft.js', html)
        js = (STATIC / 'js' / 'enquiry-draft.js').read_text()
        self.assertIn('7 * 24 * 60 * 60 * 1000', js)      # kept 7 days at most
        self.assertNotIn('consent_given', js)               # the consent tick is never kept
        self.assertNotIn('fetch(', js)                      # never sent anywhere

    def test_expired_form_page_says_the_text_was_kept(self):
        self.assertIn('what you typed is kept on this device',
                      (Path(settings.BASE_DIR) / 'templates' / '403_csrf.html').read_text())

    def test_cookie_policy_lists_it(self):
        self.assertContains(self.client.get('/cookies/'), 'dr_enquiry_draft')


class NoResultsTests(TestCase):
    def setUp(self):
        cat = Category.objects.create(name='Spices', slug='spices')
        Product.objects.create(name='Heera Chilli Powder', slug='hcp', category=cat, is_published=True)

    def test_no_results_names_the_search_gives_tips_and_offers_to_ask(self):
        html = self.client.get('/products/?q=saffron threads').content.decode()
        self.assertIn('No products found for “saffron threads”', html)
        self.assertIn('Check the spelling', html)
        self.assertIn('href="/contact/?ask=saffron%20threads"', html)
        self.assertIn('Clear search and filters', html)
        self.assertNotIn('<h4>No Products Found', html)   # heading order: h1 then h2

    def test_ask_link_prefills_the_enquiry_message_safely(self):
        response = self.client.get('/contact/', {'ask': 'saffron <b>threads</b>\nBcc: x@y.z'})
        message = response.context['form'].initial['message']
        self.assertIn('couldn\'t find "saffron <b>threads</b> Bcc: x@y.z"', message)   # one line only
        self.assertNotIn('\n', message)
        self.assertNotContains(response, '<b>threads</b>')                           # shown as text, never as HTML
        long = self.client.get('/contact/', {'ask': 'x' * 500}).context['form'].initial['message']
        self.assertLess(len(long), 200)

    def test_product_enquiry_wins_over_ask(self):
        product = Product.objects.get()
        message = self.client.get('/contact/', {'product_id': product.pk, 'ask': 'other'}).context['form'].initial['message']
        self.assertIn('Heera Chilli Powder', message)


class BotTrapAccessibilityTests(TestCase):
    def test_bot_trap_has_no_label_and_is_hidden_from_screen_readers(self):
        html = self.client.get('/contact/').content.decode()
        self.assertNotIn('Leave this field blank', html)
        field = re.search(r'<input[^>]*name="website"[^>]*>', html).group(0)
        self.assertIn('aria-hidden="true"', field)
        self.assertIn('tabindex="-1"', field)
