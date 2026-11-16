"""Catalogue listing, search, filters, paging, sitemap and query-count checks."""
from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from .models import Brand, Category, PackSize, Product, ProductImage


def make_products(category, brand, count, start=0, published=True):
    """Products with a pack size and a photo record each (bulk_create skips image processing)."""
    products = Product.objects.bulk_create([
        Product(name=f'Product {i:03d}', slug=f'product-{i:03d}', sku=f'SKU{i:03d}',
                category=category, brand=brand, is_published=published)
        for i in range(start, start + count)
    ])
    PackSize.objects.bulk_create([PackSize(product=p, size='6 x 1 kg') for p in products])
    ProductImage.objects.bulk_create([
        ProductImage(product=p, image=f'products/{p.slug}.jpg', thumbnail=f'products/thumbnails/{p.slug}_card.jpg',
                     alt_text=p.name, is_primary=True)
        for p in products
    ])
    return products


class CatalogueListingTests(TestCase):
    def setUp(self):
        self.spices = Category.objects.create(name='Spices & Masalas', slug='spices-masalas', display_order=1)
        self.rice = Category.objects.create(name='Rice', slug='rice', display_order=2)
        self.hidden_cat = Category.objects.create(name='Old', slug='old', is_active=False)
        self.heera = Brand.objects.create(name='Heera', slug='heera')
        self.trs = Brand.objects.create(name='TRS', slug='trs')

    def names(self, response):
        return [p.name for p in response.context['page_obj']]

    # ---- paging ----
    def test_24_products_per_page_and_bad_page_numbers_fall_back(self):
        make_products(self.spices, self.heera, 30)
        first = self.client.get('/products/')
        self.assertEqual(len(first.context['page_obj']), 24)
        second = self.client.get('/products/?page=2')
        self.assertEqual(len(second.context['page_obj']), 6)
        for bad in ('abc', '-1', '0'):
            response = self.client.get(f'/products/?page={bad}')
            self.assertEqual(response.status_code, 200, bad)
        self.assertEqual(self.client.get('/products/?page=999').context['page_obj'].number, 2)

    # ---- no N+1 queries ----
    def test_query_count_does_not_grow_with_products(self):
        make_products(self.spices, self.heera, 3)
        with CaptureQueriesContext(connection) as small:
            self.client.get('/products/')
        make_products(self.rice, self.trs, 21, start=100)
        with CaptureQueriesContext(connection) as full:
            self.client.get('/products/')
        self.assertEqual(len(small), len(full), 'Each product card must not add database queries')

    def test_home_page_query_count_does_not_grow(self):
        make_products(self.spices, self.heera, 2)
        with CaptureQueriesContext(connection) as small:
            self.client.get('/')
        for i in range(10):
            Category.objects.create(name=f'Cat {i}', slug=f'cat-{i}', show_on_home=True)
            Brand.objects.create(name=f'Brand {i}', slug=f'brand-{i}', is_featured=True)
        with CaptureQueriesContext(connection) as full:
            self.client.get('/')
        self.assertEqual(len(small), len(full), 'Category circles and brand badges must not add queries')

    # ---- search ----
    def test_search_matches_name_brand_category_and_code_ignoring_case(self):
        Product.objects.create(name='Heera Chilli Powder', slug='hcp', sku='22029', category=self.spices,
                               brand=self.heera, is_published=True)
        Product.objects.create(name='TRS Basmati', slug='trs-basmati', sku='T1', category=self.rice,
                               brand=self.trs, is_published=True)
        self.assertEqual(self.names(self.client.get('/products/?q=CHILLI')), ['Heera Chilli Powder'])
        self.assertEqual(self.names(self.client.get('/products/?q=trs')), ['TRS Basmati'])
        self.assertEqual(self.names(self.client.get('/products/?q=rice')), ['TRS Basmati'])
        self.assertEqual(self.names(self.client.get('/products/?q=22029')), ['Heera Chilli Powder'])

    def test_search_and_filters_never_show_unpublished_products(self):
        Product.objects.create(name='Draft Chilli', slug='draft-chilli', category=self.spices, brand=self.heera,
                               is_published=False)
        for url in ('/products/?q=draft', '/products/?category=spices-masalas', '/products/?brand=heera', '/products/'):
            self.assertNotIn('Draft Chilli', self.names(self.client.get(url)), url)
        self.assertEqual(self.client.get('/products/draft-chilli/').status_code, 404)

    def test_search_text_is_escaped_not_run(self):
        response = self.client.get('/products/', {'q': '<script>alert(1)</script>'})
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, '<script>alert(1)</script>')
        self.assertContains(response, '&lt;script&gt;alert(1)&lt;/script&gt;')

    def test_very_long_search_does_not_break_the_page(self):
        response = self.client.get('/products/', {'q': 'masala ' * 400})
        self.assertEqual(response.status_code, 200)

    # ---- filters and sorting ----
    def test_category_and_brand_filters_combine(self):
        Product.objects.create(name='Heera Rice', slug='heera-rice', category=self.rice, brand=self.heera, is_published=True)
        Product.objects.create(name='TRS Rice', slug='trs-rice', category=self.rice, brand=self.trs, is_published=True)
        Product.objects.create(name='Heera Chilli', slug='heera-chilli', category=self.spices, brand=self.heera, is_published=True)
        response = self.client.get('/products/?category=rice&brand=heera')
        self.assertEqual(self.names(response), ['Heera Rice'])

    def test_unknown_or_hidden_category_and_unknown_brand_give_404(self):
        self.assertEqual(self.client.get('/products/?category=nope').status_code, 404)
        self.assertEqual(self.client.get('/products/?category=old').status_code, 404)
        self.assertEqual(self.client.get('/products/?brand=nope').status_code, 404)

    def test_unknown_sort_falls_back_to_recommended_order(self):
        Product.objects.create(name='B Rice', slug='b-rice', category=self.rice, is_published=True)
        Product.objects.create(name='Z Spice', slug='z-spice', category=self.spices, is_published=True)
        response = self.client.get('/products/?sort=price;DROP TABLE')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context['active_sort'], 'recommended')
        # Recommended follows the category display order: spices (1) before rice (2)
        self.assertEqual(self.names(response), ['Z Spice', 'B Rice'])

    def test_old_category_and_brand_addresses_redirect(self):
        self.assertRedirects(self.client.get('/categories/rice/'), '/products/?category=rice', fetch_redirect_response=False)
        self.assertRedirects(self.client.get('/brands/heera/'), '/products/?brand=heera', fetch_redirect_response=False)

    # ---- sitemap ----
    def test_sitemap_lists_published_products_only(self):
        Product.objects.create(name='Live', slug='live-one', category=self.rice, is_published=True)
        Product.objects.create(name='Draft', slug='draft-one', category=self.rice, is_published=False)
        response = self.client.get('/sitemap.xml')
        self.assertContains(response, '/products/live-one/')
        self.assertNotContains(response, '/products/draft-one/')
        self.assertNotContains(response, 'category=old')
