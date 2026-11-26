"""Google indexing tidy-up (26 Nov 2026).

Search Console reported Soft 404, "Duplicate, Google chose different canonical" and redirects.
Empty filter pages leave the sitemap and are noindex, searches are noindex, the canonical link
drops tracking/search/sort bits and www, and old /categories/ and /brands/<slug>/ links are 301s.
"""
import html as htmllib
import re

from django.core.cache import cache
from django.test import TestCase, override_settings

from catalogue.models import Brand, Category, Product
from pages.models import FAQ

CANON = re.compile(r'<link rel="canonical" href="([^"]*)">')
NOINDEX = '<meta name="robots" content="noindex, follow">'


@override_settings(ALLOWED_HOSTS=['testserver', 'desiroots.co.uk', 'www.desiroots.co.uk'])
class IndexingTests(TestCase):
    def setUp(self):
        cache.clear()
        self.full_cat = Category.objects.create(name='Rice', slug='rice')
        self.empty_cat = Category.objects.create(name='Pickles', slug='pickles')
        self.full_brand = Brand.objects.create(name='TRS', slug='trs')
        self.empty_brand = Brand.objects.create(name='MTR', slug='mtr')
        self.hidden_brand = Brand.objects.create(name='Hidden', slug='hidden')
        Product.objects.create(name='Basmati', slug='basmati', category=self.full_cat,
                               brand=self.full_brand, is_published=True)
        Product.objects.create(name='Draft', slug='draft', category=self.empty_cat,
                               brand=self.hidden_brand, is_published=False)

    def get(self, path, **extra):
        cache.clear()
        return self.client.get(path, **extra).content.decode()

    def canon(self, path, **extra):
        return htmllib.unescape(CANON.search(self.get(path, **extra)).group(1))

    # Sitemap
    def test_sitemap_lists_only_filters_with_published_products(self):
        xml = self.get('/sitemap.xml')
        self.assertIn('/products/?category=rice<', xml)
        self.assertIn('/products/?brand=trs<', xml)
        for gone in ('category=pickles', 'brand=mtr', 'brand=hidden', '/products/draft/'):
            self.assertNotIn(gone, xml)
        self.assertIn('/brands/<', xml)

    def test_sitemap_has_no_repeats(self):
        locs = re.findall(r'<loc>([^<]*)', self.get('/sitemap.xml'))
        self.assertEqual(len(locs), len(set(locs)))

    # Noindex
    def test_empty_filter_page_is_noindex_but_still_shown(self):
        r = self.client.get('/products/?category=pickles')
        self.assertEqual(r.status_code, 200)
        self.assertIn(NOINDEX, r.content.decode())

    def test_search_results_are_noindex(self):
        self.assertIn(NOINDEX, self.get('/products/?q=basmati'))
        self.assertIn(NOINDEX, self.get('/products/?q=zzzz'))

    def test_real_pages_stay_indexable(self):
        for path in ('/', '/products/', '/products/?category=rice', '/products/?brand=trs',
                     '/products/basmati/', '/brands/', '/about/', '/contact/'):
            self.assertNotIn('noindex', self.get(path), path)

    def test_faq_noindex_only_while_it_has_no_answers(self):
        self.assertIn(NOINDEX, self.get('/faq/'))
        FAQ.objects.create(question='Do you deliver?', answer='Yes.', is_active=True)
        self.assertNotIn('noindex', self.get('/faq/'))

    # Canonical
    def test_canonical_keeps_only_real_filters_and_pages(self):
        self.assertEqual(self.canon('/products/?brand=trs&utm_source=x&fbclid=y&sort=name'),
                         'http://testserver/products/?brand=trs')
        self.assertEqual(self.canon('/products/?category=rice&page=2'),
                         'http://testserver/products/?category=rice&page=2')
        self.assertEqual(self.canon('/products/?page=1'), 'http://testserver/products/')
        self.assertEqual(self.canon('/products/?page=abc'), 'http://testserver/products/')
        self.assertEqual(self.canon('/products/?q=rice'), 'http://testserver/products/')

    def test_canonical_on_other_pages_ignores_query_strings(self):
        self.assertEqual(self.canon('/?page=2&utm_source=x'), 'http://testserver/')
        self.assertEqual(self.canon('/about/?category=rice'), 'http://testserver/about/')
        self.assertEqual(self.canon('/products/basmati/?ref=abc'), 'http://testserver/products/basmati/')

    def test_canonical_never_points_at_www(self):
        self.assertEqual(self.canon('/about/', HTTP_HOST='www.desiroots.co.uk'), 'http://desiroots.co.uk/about/')

    def test_canonical_cannot_be_used_to_inject_html(self):
        html = self.get('/products/?brand="><script>alert(1)</script>')
        self.assertNotIn('<script>alert(1)', html)
        html = self.get('/products/?brand=trs&page="><script>x</script>')
        self.assertNotIn('<script>x', html)

    # Redirects
    def test_old_category_and_brand_links_are_permanent(self):
        r = self.client.get('/categories/rice/')
        self.assertEqual((r.status_code, r['Location']), (301, '/products/?category=rice'))
        r = self.client.get('/brands/trs/')
        self.assertEqual((r.status_code, r['Location']), (301, '/products/?brand=trs'))
