from django.contrib.sitemaps import Sitemap
from django.db.models import Count, Q
from django.urls import reverse
from catalogue.models import Product, Category, Brand

class ProductSitemap(Sitemap):
    changefreq = 'weekly'
    priority = 0.8

    def items(self):
        return Product.objects.filter(is_published=True).order_by('name')

    def location(self, item):
        return f'/products/{item.slug}/'


class CategorySitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.6

    def items(self):
        # Only categories with published products: an empty filter page is a "soft 404" to Google
        return (Category.objects.filter(is_active=True)
                .annotate(n=Count('products', filter=Q(products__is_published=True)))
                .filter(n__gt=0).order_by('display_order', 'name'))

    def location(self, item):
        return f'/products/?category={item.slug}'


class BrandSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.5

    def items(self):
        # Only brands with published products (see CategorySitemap)
        return (Brand.objects.annotate(n=Count('products', filter=Q(products__is_published=True)))
                .filter(n__gt=0).order_by('name'))

    def location(self, item):
        return f'/products/?brand={item.slug}'


class StaticViewSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.5

    def items(self):
        return ['pages:home', 'catalogue:brand_list', 'pages:about', 'pages:contact', 'pages:faq_list']

    def location(self, item):
        return reverse(item)
