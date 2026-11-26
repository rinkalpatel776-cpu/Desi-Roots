from django.shortcuts import render

from core.page_cache import cache_public_page
from catalogue.models import Category, Brand, Product
from .models import FAQ, Testimonial

def _rounded(n, step):
    """1931 -> '1,900+' so the hero never over-states; small numbers are shown exactly."""
    if n < step:
        return str(n)
    return f"{(n // step) * step:,}+"


def _hero_stats():
    """Counts for the home hero chips, taken from the live catalogue (published products only)."""
    published = Product.objects.filter(is_published=True)
    return {
        'products': _rounded(published.count(), 100),
        'brands': _rounded(Brand.objects.filter(products__is_published=True).distinct().count(), 10),
        'categories': Category.objects.filter(is_active=True, products__is_published=True).distinct().count(),
    }


@cache_public_page
def home(request):
    # Up to 24 categories ticked "Show on home page" in the admin, in display order
    # (the first 24 with published products if none are ticked)
    categories = Category.for_home_page()[:Category.HOME_PAGE_LIMIT]
    
    # Retrieve featured products (published + featured) with optimizations
    featured_products = (
        Product.objects.filter(is_published=True, is_featured=True)
        .select_related('category', 'brand')
        .prefetch_related('images', 'pack_sizes')[:4]
    )
    
    # Brands ticked "Show on home page" in the admin, in their chosen order, for the
    # Shop by Brand slider. The section hides itself when none are ticked.
    featured_brands = Brand.ticked_for_home_page()[:Brand.HOME_PAGE_LIMIT]

    # Retrieve testimonials
    testimonials = Testimonial.objects.filter(is_active=True)

    # Retrieve FAQs preview (first 4 items)
    faqs = FAQ.objects.filter(is_active=True).order_by('display_order', 'id')[:4]

    context = {
        'hero_stats': _hero_stats(),
        'categories': categories,
        'featured_products': featured_products,
        'featured_brands': featured_brands,
        'testimonials': testimonials,
        'faqs': faqs,
    }
    return render(request, 'pages/home.html', context)


from enquiries.views import handle_enquiry_form

@cache_public_page
def about(request):
    return render(request, 'pages/about.html')


def contact(request):
    return handle_enquiry_form(request, 'pages/contact.html')


@cache_public_page
def faq_list(request):
    faqs = FAQ.objects.filter(is_active=True).order_by('display_order', 'id')
    context = {
        'faqs': faqs,
        # "Answers coming soon" is a thin page to Google; index it once real answers are added
        'robots_noindex': not faqs,
    }
    return render(request, 'pages/faq.html', context)


@cache_public_page
def privacy(request):
    return render(request, 'pages/legal/privacy.html')


@cache_public_page
def cookies(request):
    return render(request, 'pages/legal/cookies.html')


@cache_public_page
def terms(request):
    return render(request, 'pages/legal/terms.html')
