from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from catalogue.models import Brand


class HomeFeaturedBrandsTests(TestCase):
    def get_brand_names(self):
        response = self.client.get(reverse('pages:home'))
        self.assertEqual(response.status_code, 200)
        return [b.name for b in response.context['featured_brands']]

    def test_only_ticked_brands_are_shown(self):
        Brand.objects.create(name='Shown', slug='shown', is_featured=True)
        Brand.objects.create(name='Hidden', slug='hidden', is_featured=False)
        self.assertEqual(self.get_brand_names(), ['Shown'])

    def test_brands_are_capped_at_the_limit_in_order(self):
        limit = Brand.HOME_PAGE_LIMIT
        for i in range(limit + 2):
            Brand.objects.create(name=f'Brand {i:02d}', slug=f'brand-{i}', is_featured=True, home_order=limit + 2 - i)
        expected = [f'Brand {i:02d}' for i in range(limit + 1, 1, -1)]
        self.assertEqual(self.get_brand_names(), expected)

    def test_brands_follow_home_order_then_name(self):
        Brand.objects.create(name='Zeta', slug='zeta', is_featured=True, home_order=1)
        Brand.objects.create(name='Beta', slug='beta', is_featured=True, home_order=2)
        Brand.objects.create(name='Alpha', slug='alpha', is_featured=True, home_order=2)
        self.assertEqual(self.get_brand_names(), ['Zeta', 'Alpha', 'Beta'])

    def test_section_hidden_when_no_brands_ticked(self):
        Brand.objects.create(name='Hidden', slug='hidden', is_featured=False)
        response = self.client.get(reverse('pages:home'))
        self.assertEqual(self.get_brand_names(), [])
        self.assertNotContains(response, 'id="home-brands"')


class BrandAdminHomePageMessageTests(TestCase):
    def setUp(self):
        user = User.objects.create_superuser('staff', 'staff@example.test', 'test-pass-123')
        self.client.force_login(user)
        self.url = reverse('admin:catalogue_brand_changelist')

    def get_messages(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        return [str(m) for m in response.context['messages']]

    def test_warns_and_names_hidden_brands_when_over_limit(self):
        limit = Brand.HOME_PAGE_LIMIT
        for i in range(limit + 1):
            Brand.objects.create(name=f'Brand {i:02d}', slug=f'brand-{i}', is_featured=True, home_order=i)
        [message] = self.get_messages()
        shown = ', '.join(f'Brand {i:02d}' for i in range(limit))
        self.assertIn(f'Showing: {shown}.', message)
        self.assertIn(f'Ticked but not shown: Brand {limit:02d}.', message)

    def test_lists_shown_brands_when_within_limit(self):
        Brand.objects.create(name='Only', slug='only', is_featured=True)
        self.assertEqual(self.get_messages(), ['Home page shows: Only.'])


class HomeHeroSliderTests(TestCase):
    """Home hero slider (18 Nov 2026): spice-merchant photo, welcome slide, then the MDH slide."""

    def setUp(self):
        from catalogue.models import Category, Product
        self.cat = Category.objects.create(name='Spices', slug='spices')
        self.Product = Product

    def html(self):
        response = self.client.get(reverse('pages:home'))
        self.assertEqual(response.status_code, 200)
        return response.content.decode()

    def test_one_h1_and_both_slides_with_controls(self):
        html = self.html()
        self.assertEqual(html.count('<h1'), 1)
        # The one h1 sits outside the slides, so it is never hidden when a slide moves away
        h1 = html.index('<h1'); first_slide = html.index('class="hs-slide')
        self.assertLess(h1, first_slide)
        self.assertIn('Your Trusted Wholesale Partner for', html)
        self.assertIn('MDH Supplier', html)
        self.assertEqual(html.count('aria-roledescription="slide"'), 3)
        self.assertLess(html.index('sp-hero-wrapper'), html.index('h10-title'))  # old photo hero is slide 1
        self.assertLess(html.index('h10-title'), html.index('hs-mdh-title'))
        for label in ('Previous slide', 'Next slide', 'Show slide 1', 'Show slide 2', 'Show slide 3', 'Pause slides'):
            self.assertIn(f'aria-label="{label}"', html)
        self.assertIn('href="/products/?brand=mdh"', html)

    def test_slider_code_and_styles_are_files_not_inline(self):
        # The site's Content-Security-Policy only allows inline scripts it already knows (by hash)
        html = self.html()
        self.assertIn('/static/js/hero-slider.js?v=1', html)
        self.assertIn('/static/css/home-hero.css?v=3', html)
        self.assertNotIn('setInterval', html)

    def test_slider_moves_every_5_seconds_and_respects_reduced_motion(self):
        from pathlib import Path
        from django.conf import settings
        js = (Path(settings.BASE_DIR) / 'static' / 'js' / 'hero-slider.js').read_text()
        self.assertIn('5000', js)
        self.assertIn('prefers-reduced-motion', js)
        self.assertIn("'inert'", js)  # hidden slide's links can't be tabbed to

    def test_counts_come_from_the_catalogue_and_never_overstate(self):
        from pages.views import _rounded
        self.assertEqual(_rounded(1931, 100), '1,900+')
        self.assertEqual(_rounded(22, 10), '20+')
        self.assertEqual(_rounded(7, 10), '7')
        self.Product.objects.create(name='A', slug='a', category=self.cat, is_published=True)
        self.Product.objects.create(name='B', slug='b', category=self.cat, is_published=False)
        stats = self.client.get(reverse('pages:home')).context['hero_stats']
        self.assertEqual(stats, {'products': '1', 'brands': '0', 'categories': 1})

    def test_brands_bar_lists_ticked_brands_only(self):
        Brand.objects.create(name='Shown Brand', slug='shown-brand', is_featured=True)
        Brand.objects.create(name='Unticked Brand', slug='unticked-brand', is_featured=False)
        html = self.html()
        bar = html[html.index('Brands we stock:'):][:300]
        self.assertIn('Shown Brand', bar)
        self.assertNotIn('Unticked Brand', bar)

    def test_hero_images_exist(self):
        from pathlib import Path
        from django.conf import settings
        folder = Path(settings.BASE_DIR) / 'static' / 'images' / 'hero'
        for name in ('hero-packs-1400.webp', 'hero-packs-700.webp', 'mdh-slide-1600.webp',
                     'mdh-slide-1000.webp', 'mdh-slide-phone-900.webp'):
            self.assertTrue((folder / name).exists(), name)
