from django.shortcuts import render
from catalogue.models import Category, Brand, Product
from .models import FAQ, Testimonial

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
