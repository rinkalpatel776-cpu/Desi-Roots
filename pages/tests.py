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

    def test_every_ticked_brand_is_shown(self):
        for i in range(9):
            Brand.objects.create(name=f'Brand {i}', slug=f'brand-{i}', is_featured=True)
        self.assertEqual(len(self.get_brand_names()), 9)

    def test_brands_follow_home_order_then_name(self):
        Brand.objects.create(name='Zeta', slug='zeta', is_featured=True, home_order=1)
        Brand.objects.create(name='Beta', slug='beta', is_featured=True, home_order=2)
        Brand.objects.create(name='Alpha', slug='alpha', is_featured=True, home_order=2)
        self.assertEqual(self.get_brand_names(), ['Zeta', 'Alpha', 'Beta'])

    def test_section_hidden_when_no_brands_ticked(self):
        Brand.objects.create(name='Hidden', slug='hidden', is_featured=False)
        response = self.client.get(reverse('pages:home'))
        self.assertEqual(self.get_brand_names(), [])
        self.assertNotContains(response, 'sp-featured-brands-section')
