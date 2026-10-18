from django.db.models import Count, Q
from django.shortcuts import render
from catalogue.models import Category, Brand, Product
from .models import FAQ, Testimonial

def home(request):
    # Retrieve active categories
    # Only categories that have published products
    categories = (
        Category.objects.filter(is_active=True)
        .annotate(published_count=Count('products', filter=Q(products__is_published=True)))
        .filter(published_count__gt=0)
        .order_by('display_order', 'name')[:6]
    )
    
    # Retrieve featured products (published + featured) with optimizations
    featured_products = (
        Product.objects.filter(is_published=True, is_featured=True)
        .select_related('category', 'brand')
        .prefetch_related('images', 'pack_sizes')[:4]
    )
    
    # The first 4 brands ticked "Show on home page" in the admin, in their chosen order.
    # The section hides itself when none are ticked.
    featured_brands = Brand.ticked_for_home_page()[:Brand.HOME_PAGE_LIMIT]

    # Retrieve testimonials
    testimonials = Testimonial.objects.filter(is_active=True)

    # Retrieve FAQs preview (first 4 items)
    faqs = FAQ.objects.filter(is_active=True).order_by('display_order', 'id')[:4]

    context = {
        'categories': categories,
        'featured_products': featured_products,
        'featured_brands': featured_brands,
        'testimonials': testimonials,
        'faqs': faqs,
    }
    return render(request, 'pages/home.html', context)


from enquiries.views import handle_enquiry_form

def about(request):
    return render(request, 'pages/about.html')


def contact(request):
    return handle_enquiry_form(request, 'pages/contact.html')


def faq_list(request):
    faqs = FAQ.objects.filter(is_active=True).order_by('display_order', 'id')
    context = {
        'faqs': faqs
    }
    return render(request, 'pages/faq.html', context)


def privacy(request):
    return render(request, 'pages/legal/privacy.html')


def cookies(request):
    return render(request, 'pages/legal/cookies.html')


def terms(request):
    return render(request, 'pages/legal/terms.html')
