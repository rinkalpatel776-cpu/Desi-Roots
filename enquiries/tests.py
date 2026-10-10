from django.test import TestCase, Client, override_settings
from .models import Enquiry
from catalogue.models import Category, Product

@override_settings(TURNSTILE_SECRET_KEY='')
class EnquiryTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Setup mock category and product
        self.category = Category.objects.create(name="Spices", slug="spices")
        self.product = Product.objects.create(
            name="Turmeric Powder",
            slug="turmeric-powder",
            sku="SP-SPICE-101",
            category=self.category,
            is_published=True
        )

    def test_wholesale_form_rendering(self):
        # Access wholesale enquiry form page
        response = self.client.get('/wholesale/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Wholesale Enquiry & Contact")
        self.assertContains(response, "Submit Enquiry")

    def test_wholesale_form_prefilled_product(self):
        # Access wholesale page with preselected product parameter
        response = self.client.get(f'/wholesale/?product_id={self.product.id}')
        self.assertEqual(response.status_code, 200)
        # Verify that the product is selected in the select dropdown list
        self.assertContains(response, f'value="{self.product.id}" selected')

    def test_valid_enquiry_submission(self):
        # Submit a valid enquiry
        payload = {
            'name': 'John Doe',
            'business_name': 'Bristol Curry House',
            'business_type': 'Restaurant',
            'email': 'john@curryhouse.co.uk',
            'phone': '0117 999 9999',
            'product': self.product.id,
            'category_interest': 'Spices',
            'message': 'We need 50kg of turmeric powder weekly. Please quote.',
            'consent_given': 'on', # Checkbox is sent as 'on'
            'website': '' # Leave honeypot empty
        }
        
        # Submit POST request
        response = self.client.post('/wholesale/', data=payload)
        
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
            'business_type': 'Caterer',
            'email': 'spam@bot.com',
            'phone': '07000000000',
            'message': 'Spam message',
            'consent_given': 'on',
            'website': 'http://spambot.com' # Honeypot field filled
        }
        
        # Submit POST request
        response = self.client.post('/wholesale/', data=payload)
        
        # Verify it doesn't redirect and returns validation errors
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], None, "Spam detected.")
        self.assertEqual(Enquiry.objects.count(), 0)

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
        
        response = self.client.post('/wholesale/', data=payload)
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'name', "This field is required.")
        self.assertEqual(Enquiry.objects.count(), 0)


