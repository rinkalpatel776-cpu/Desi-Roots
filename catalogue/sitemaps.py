from django.contrib.sitemaps import Sitemap
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
        return Category.objects.filter(is_active=True).order_by('display_order')

    def location(self, item):
        return f'/products/?category={item.slug}'


class BrandSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.5

    def items(self):
        return Brand.objects.all().order_by('name')

    def location(self, item):
        return f'/products/?brand={item.slug}'


class StaticViewSitemap(Sitemap):
    changefreq = 'monthly'
    priority = 0.5

    def items(self):
        return ['pages:home', 'pages:about', 'pages:contact', 'pages:faq_list', 'enquiries:wholesale_enquiry']

    def location(self, item):
        return reverse(item)
