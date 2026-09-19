from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Q
from .models import Category, Brand, Product

def product_list(request):
    # Base query containing optimizations to prevent N+1 queries
    queryset = Product.objects.filter(is_published=True).select_related('category', 'brand').prefetch_related('images', 'pack_sizes')
    
    # Extract query parameters
    query = request.GET.get('q', '').strip()
    category_slug = request.GET.get('category', '').strip()
    brand_slug = request.GET.get('brand', '').strip()
    
    # Active filters mapping
    active_filters = {}
    
    # Apply category filter
    if category_slug:
        category = get_object_or_404(Category, slug=category_slug, is_active=True)
        queryset = queryset.filter(category=category)
        active_filters['category'] = category
        
    # Apply brand filter
    if brand_slug:
        brand = get_object_or_404(Brand, slug=brand_slug)
        queryset = queryset.filter(brand=brand)
        active_filters['brand'] = brand

    # Apply search filter (name, brand name, category name)
    if query:
        queryset = queryset.filter(
            Q(name__icontains=query) |
            Q(brand__name__icontains=query) |
            Q(category__name__icontains=query) |
            Q(sku__icontains=query)
        )
        active_filters['q'] = query

    # Pagination: 24 products per page
    paginator = Paginator(queryset, 24)
    page_number = request.GET.get('page')
    
    try:
        page_obj = paginator.get_page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.get_page(1)

    # Context items for sidebar filters
    categories = Category.objects.filter(is_active=True).order_order = ['display_order']
    categories = Category.objects.filter(is_active=True).order_by('display_order', 'name')
    brands = Brand.objects.all().order_by('name')

    context = {
        'page_obj': page_obj,
        'categories': categories,
        'brands': brands,
        'active_filters': active_filters,
    }
    return render(request, 'catalogue/product_list.html', context)


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.filter(is_published=True)
        .select_related('category', 'brand')
        .prefetch_related('images', 'pack_sizes'), 
        slug=slug
    )
    
    # Get primary image
    primary_image = product.images.filter(is_primary=True).first()
    if not primary_image:
        primary_image = product.images.first()
        
    # Related products: same category, excluding current product, limit 4
    related_products = (
        Product.objects.filter(category=product.category, is_published=True)
        .exclude(id=product.id)
        .select_related('category', 'brand')
        .prefetch_related('images', 'pack_sizes')[:4]
    )

    context = {
        'product': product,
        'primary_image': primary_image,
        'related_products': related_products,
    }
    return render(request, 'catalogue/product_detail.html', context)


def brand_list(request):
    brands = Brand.objects.all().order_by('name')
    context = {
        'brands': brands
    }
    return render(request, 'catalogue/brand_list.html', context)


def category_detail_redirect(request, slug):
    # Redirect /categories/<slug>/ to products list page filtered by category
    return redirect(f'/products/?category={slug}')


def brand_detail_redirect(request, slug):
    # Redirect /brands/<slug>/ to products list page filtered by brand
    return redirect(f'/products/?brand={slug}')
