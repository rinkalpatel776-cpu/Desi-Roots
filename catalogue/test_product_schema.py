"""Product page structured data (26 Nov 2026).

Google Search Console flagged "Missing field 'price' (in 'offers')" under Merchant listings and
Product snippets. Desi Roots has no prices, reviews or ratings (prices are quoted privately), so
product pages carry no Product/Offer markup at all, only a safely built BreadcrumbList.
"""
import json
import re

from django.core.cache import cache
from django.test import TestCase

from .models import Brand, Category, Product

LD = re.compile(r'<script type="application/ld\+json">\s*(.*?)\s*</script>', re.S)


class ProductSchemaTests(TestCase):
    def setUp(self):
        cache.clear()
        self.category = Category.objects.create(name='Rice & Grains', slug='rice-grains')
        self.brand = Brand.objects.create(name='Indus Valley', slug='indus-valley')
        self.product = Product.objects.create(
            name='Premium Basmati Rice', slug='premium-basmati-rice', sku='SP-RICE-101',
            category=self.category, brand=self.brand, description='Aged basmati.', is_published=True)

    def blocks(self, product):
        cache.clear()
        html = self.client.get(f'/products/{product.slug}/').content.decode()
        return html, [json.loads(b) for b in LD.findall(html)]

    def test_no_product_or_offer_markup_so_google_asks_for_no_price(self):
        html, blocks = self.blocks(self.product)
        types = [b.get('@type') for b in blocks]
        self.assertNotIn('Product', types)
        for word in ('"offers"', '"Offer"', '"price"', 'priceCurrency', 'aggregateRating', '"review"'):
            self.assertNotIn(word, html)

    def test_breadcrumb_is_valid_json_with_real_links(self):
        _, blocks = self.blocks(self.product)
        crumbs = [b for b in blocks if b.get('@type') == 'BreadcrumbList']
        self.assertEqual(len(crumbs), 1)
        items = crumbs[0]['itemListElement']
        self.assertEqual([i['name'] for i in items],
                         ['Home', 'Products', 'Rice & Grains', 'Premium Basmati Rice'])
        self.assertEqual([i['position'] for i in items], [1, 2, 3, 4])
        self.assertTrue(items[2]['item'].endswith('/products/?category=rice-grains'))
        self.assertTrue(items[3]['item'].endswith('/products/premium-basmati-rice/'))
        for path in [items[2]['item'].split('testserver')[1], items[3]['item'].split('testserver')[1]]:
            self.assertEqual(self.client.get(path).status_code, 200)

    def test_hostile_product_name_cannot_break_the_json_or_the_script_tag(self):
        nasty = Product.objects.create(
            name='Chilli "Hot" </script><script>alert(1)</script> \\ Mix', slug='nasty-mix',
            category=self.category, brand=self.brand, is_published=True)
        html, blocks = self.blocks(nasty)
        self.assertNotIn('<script>alert(1)', html)
        crumbs = [b for b in blocks if b.get('@type') == 'BreadcrumbList'][0]
        self.assertEqual(crumbs['itemListElement'][3]['name'], nasty.name)

    def test_whole_site_business_markup_still_present(self):
        _, blocks = self.blocks(self.product)
        self.assertTrue(any('@graph' in b for b in blocks))
