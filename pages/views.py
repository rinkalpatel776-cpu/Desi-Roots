from django.shortcuts import render
from catalogue.models import Category, Brand, Product
from .models import FAQ, Testimonial

def home(request):
    # Retrieve active categories
    categories = Category.objects.filter(is_active=True).order_by('display_order', 'name')[:6]
    
    # Retrieve featured products (published + featured) with optimizations
    featured_products = (
        Product.objects.filter(is_published=True, is_featured=True)
        .select_related('category', 'brand')
        .prefetch_related('images', 'pack_sizes')[:4]
    )
    
    # Retrieve featured brands
    featured_brands = Brand.objects.filter(is_featured=True)[:6]
    if not featured_brands.exists():
        featured_brands = Brand.objects.all()[:6]

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


from django.conf import settings
from enquiries.forms import EnquiryForm

def about(request):
    return render(request, 'pages/about.html')


def contact(request):
    form = EnquiryForm()
    context = {
        'form': form,
        'turnstile_site_key': settings.TURNSTILE_SITE_KEY,
    }
    return render(request, 'pages/contact.html', context)


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
