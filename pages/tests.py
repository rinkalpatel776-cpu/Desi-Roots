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
