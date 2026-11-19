"""Page cache (20 Nov 2026): fast repeat visits, but the owner's edits always show at once."""
import tempfile

from django.contrib.auth.models import User
from django.core.cache import cache
from django.test import TestCase, TransactionTestCase, override_settings

from catalogue.models import Brand, Category, PackSize, Product
from core.models import SiteSettings
from pages.models import FAQ

TMP_CACHE = tempfile.mkdtemp(prefix='dr-cache-test-')


@override_settings(PAGE_CACHE_SECONDS=600, CACHES={'default': {
    'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache', 'LOCATION': TMP_CACHE}})
class PageCacheTests(TransactionTestCase):  # real commits, so the after-save refresh runs as on the server
    def setUp(self):
        cache.clear()
        self.cat = Category.objects.create(name='Spices', slug='spices')
        self.product = Product.objects.create(name='Heera Chilli Powder', slug='heera-chilli-powder',
                                              category=self.cat, is_published=True)

    def get(self, path, **extra):
        return self.client.get(path, **extra)

    def test_second_visit_is_served_from_the_cache(self):
        first = self.get('/products/')
        second = self.get('/products/')
        self.assertEqual(first['X-Page-Cache'], 'miss')
        self.assertEqual(second['X-Page-Cache'], 'hit')
        self.assertEqual(first.content, second.content)

    def test_editing_a_product_shows_at_once(self):
        self.get('/products/')
        self.product.name = 'Heera Extra Hot Chilli Powder'
        self.product.save()
        response = self.get('/products/')
        self.assertEqual(response['X-Page-Cache'], 'miss')
        self.assertContains(response, 'Heera Extra Hot Chilli Powder')

    def test_new_and_unpublished_products_show_or_hide_at_once(self):
        self.get('/products/')
        Product.objects.create(name='East End Turmeric', slug='east-end-turmeric', category=self.cat, is_published=True)
        self.assertContains(self.get('/products/'), 'East End Turmeric')
        self.product.is_published = False
        self.product.save()
        self.assertNotContains(self.get('/products/'), 'Heera Chilli Powder')

    def test_pack_sizes_brands_faqs_and_site_settings_refresh_the_pages(self):
        for change in (
            lambda: PackSize.objects.create(product=self.product, size='6 x 1 kg'),
            lambda: Brand.objects.create(name='Fresh Brand', slug='fresh-brand', is_featured=True),
            lambda: FAQ.objects.create(question='Do you deliver?', answer='Yes', is_active=True),
            lambda: SiteSettings.objects.update_or_create(pk=SiteSettings.objects.first().pk if SiteSettings.objects.exists() else None,
                                                          defaults={'announcement_bar': 'NEW BAR MESSAGE'}),
        ):
            self.get('/')
            change()
            self.assertEqual(self.get('/')['X-Page-Cache'], 'miss')

    def test_deleting_refreshes_too(self):
        self.get('/products/')
        self.product.delete()
        self.assertNotContains(self.get('/products/'), 'Heera Chilli Powder')

    def test_searches_staff_and_the_contact_form_are_never_cached(self):
        self.get('/products/?q=chilli')
        self.assertNotIn('X-Page-Cache', self.get('/products/?q=chilli'))
        self.get('/contact/')
        self.assertNotIn('X-Page-Cache', self.get('/contact/'))
        staff = User.objects.create_user('staff-test', password='x-very-long-password-1', is_staff=True)
        self.client.force_login(staff)
        self.assertNotIn('X-Page-Cache', self.get('/products/'))

    def test_contact_form_token_is_fresh_for_every_visitor(self):
        a = self.client_class().get('/contact/').content
        b = self.client_class().get('/contact/').content
        self.assertNotEqual(a, b)  # each visitor gets their own form token

    def test_missing_pages_are_not_cached(self):
        self.assertEqual(self.get('/products/no-such-product/').status_code, 404)
        self.assertEqual(self.get('/products/no-such-product/').status_code, 404)

    def test_each_address_and_filter_is_kept_separately(self):
        Category.objects.create(name='Rice', slug='rice')
        self.assertEqual(self.get('/products/?category=spices')['X-Page-Cache'], 'miss')
        self.assertEqual(self.get('/products/?category=rice')['X-Page-Cache'], 'miss')
        self.assertEqual(self.get('/products/?category=spices')['X-Page-Cache'], 'hit')

    def test_footer_categories_refresh_with_the_pages(self):
        self.get('/')
        Category.objects.create(name='Frozen Foods', slug='frozen-foods', is_active=True)
        Product.objects.create(name='Frozen Peas', slug='frozen-peas', category=Category.objects.get(slug='frozen-foods'),
                               is_published=True)
        self.assertIsNone(cache.get('footer_categories'))


class PageCacheOffByDefaultTests(TestCase):
    def test_development_and_tests_run_without_the_page_cache(self):
        self.assertNotIn('X-Page-Cache', self.client.get('/'))


@override_settings(PAGE_CACHE_SECONDS=600, CACHES={'default': {
    'BACKEND': 'django.core.cache.backends.filebased.FileBasedCache', 'LOCATION': TMP_CACHE}})
class BulkChangesRefreshTests(TransactionTestCase):
    """Admin bulk actions use .update(), which sends no save signal; they must refresh the pages themselves."""

    def test_bulk_unpublish_and_publish_in_the_admin_refresh_the_catalogue(self):
        from django.conf import settings as s
        from catalogue.models import ProductImage
        cache.clear()
        cat = Category.objects.create(name='Spices', slug='spices')
        product = Product.objects.create(name='Heera Chilli Powder', slug='hcp', category=cat, is_published=True)
        ProductImage.objects.bulk_create([ProductImage(product=product, image='products/x.jpg', alt_text='x')])
        admin = User.objects.create_superuser('admin-test', 'a@example.com', 'x-very-long-password-1')
        anon = self.client_class()
        self.assertContains(anon.get('/products/'), 'Heera Chilli Powder')
        self.client.force_login(admin)
        url = f'/{s.ADMIN_URL_PATH}/catalogue/product/'
        self.client.post(url, {'action': 'make_unpublished', '_selected_action': [product.pk]})
        self.assertNotContains(anon.get('/products/'), 'Heera Chilli Powder')
        self.client.post(url, {'action': 'make_published', '_selected_action': [product.pk]})
        self.assertContains(anon.get('/products/'), 'Heera Chilli Powder')
