"""SEO / AEO / GEO report fixes (23 Nov 2026): structured data, skip link, loading order, hero WebP."""
import json
import re
from pathlib import Path

from django.conf import settings
from django.test import TestCase

from catalogue.models import Brand, Category, Product
from core.models import SiteSettings
from pages.models import FAQ


def json_ld(html):
    return [json.loads(block) for block in
            re.findall(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', html, re.S)]


def find_type(blocks, wanted):
    for block in blocks:
        for item in block.get('@graph', [block]):
            types = item.get('@type')
            if wanted == types or (isinstance(types, list) and wanted in types):
                return item
    return None


class StructuredDataTests(TestCase):
    def setUp(self):
        SiteSettings.objects.update_or_create(pk=1, defaults={
            'phone_number': '+44 7000 000000', 'email_address': 'sales@example.com',
            'vat_number': 'GB 123 4567 89', 'facebook_url': 'https://www.facebook.com/example'})

    def test_home_describes_the_wholesale_business_and_site_search(self):
        blocks = json_ld(self.client.get('/').content.decode())
        business = find_type(blocks, 'WholesaleStore')
        self.assertIsNotNone(business)
        self.assertEqual(business['legalName'], 'Desi Roots Ltd')
        self.assertEqual(business['telephone'], '+44 7000 000000')       # from Site Settings, never typed in
        self.assertEqual(business['email'], 'sales@example.com')
        self.assertEqual(business['vatID'], 'GB123456789')
        self.assertEqual(business['sameAs'], ['https://www.facebook.com/example'])
        self.assertEqual(business['address'], {'@type': 'PostalAddress', 'addressLocality': 'Bristol', 'addressCountry': 'GB'})
        self.assertNotIn('streetAddress', json.dumps(blocks))            # home address kept out on purpose
        self.assertNotIn('Cardiff', json.dumps(blocks))
        search = find_type(blocks, 'WebSite')['potentialAction']
        self.assertTrue(search['target']['urlTemplate'].endswith('/products/?q={search_term_string}'))

    def test_values_are_escaped_safely(self):
        SiteSettings.objects.filter(pk=1).update(phone_number='</script><script>alert(1)</script>')
        html = self.client.get('/').content.decode()
        self.assertNotIn('</script><script>alert(1)', html)
        self.assertEqual(find_type(json_ld(html), 'WholesaleStore')['telephone'], '</script><script>alert(1)</script>')

    def test_catalogue_and_brands_have_breadcrumbs(self):
        for path, name in (('/products/', 'Products'), ('/brands/', 'Brands')):
            crumbs = find_type(json_ld(self.client.get(path).content.decode()), 'BreadcrumbList')
            self.assertEqual([i['name'] for i in crumbs['itemListElement']], ['Home', name], path)

    def test_faq_markup_only_once_there_are_answers(self):
        self.assertIsNone(find_type(json_ld(self.client.get('/faq/').content.decode()), 'FAQPage'))
        FAQ.objects.create(question='Do you deliver to Bath?', answer='Yes, weekly.', is_active=True)
        FAQ.objects.create(question='Hidden', answer='No', is_active=False)
        faq = find_type(json_ld(self.client.get('/faq/').content.decode()), 'FAQPage')
        self.assertEqual([q['name'] for q in faq['mainEntity']], ['Do you deliver to Bath?'])
        self.assertEqual(faq['mainEntity'][0]['acceptedAnswer']['text'], 'Yes, weekly.')


class AccessibilityAndLoadingTests(TestCase):
    def setUp(self):
        cat = Category.objects.create(name='Spices', slug='spices', show_on_home=True)
        Brand.objects.create(name='Heera', slug='heera', is_featured=True)
        Product.objects.create(name='Heera Chilli Powder', slug='hcp', category=cat, is_published=True)

    def test_skip_link_jumps_to_the_main_content(self):
        html = self.client.get('/').content.decode()
        self.assertLess(html.index('Skip to main content'), html.index('<nav'))   # first thing a keyboard reaches
        self.assertIn('href="#main-content"', html)
        self.assertIn('<main id="main-content"', html)

    def test_lower_images_wait_and_bootstrap_does_not_block(self):
        html = self.client.get('/').content.decode()
        lower = html[html.index('id="home-categories"'):]
        for tag in re.findall(r'<img[^>]+>', lower):
            self.assertIn('loading="lazy"', tag)
        self.assertRegex(html, r'bootstrap\.bundle\.min\.js"[^>]*\sdefer')

    def test_desktop_hero_photo_is_webp_and_preloaded(self):
        html = self.client.get('/').content.decode()
        self.assertIn('hero-ethnic-grocery-1400.webp', html)
        self.assertIn('hero-ethnic-grocery.webp', html)
        images = Path(settings.BASE_DIR) / 'static' / 'images'
        self.assertLess((images / 'hero-ethnic-grocery-1400.webp').stat().st_size, 300_000)
        css = (Path(settings.BASE_DIR) / 'static' / 'css' / 'style.css').read_text()
        self.assertNotIn("url('../images/hero-ethnic-grocery.jpg')", css)
