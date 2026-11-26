from urllib.parse import urlencode

from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.db.models import Count, Q
from .models import Category, Brand, Product
from core.page_cache import cache_public_page

# Catalogue sort options: ?sort= value -> (label, ordering). The first one is the default.
SORT_OPTIONS = {
    # Default: key staples first (spices, lentils, rice, flour...), following the category
    # "Display order" set in the admin, then A–Z within each category
    'recommended': ('Recommended', ('category__display_order', 'category__name', 'name', 'pk')),
    'name': ('Name A–Z', ('name',)),
    'name-desc': ('Name Z–A', ('-name',)),
    'brand': ('Brand', ('brand__name', 'name')),
    'category': ('Category', ('category__name', 'name')),
}
DEFAULT_SORT = 'recommended'


@cache_public_page
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

    sort = request.GET.get('sort', DEFAULT_SORT)
    if sort not in SORT_OPTIONS:
        sort = DEFAULT_SORT
    queryset = queryset.order_by(*SORT_OPTIONS[sort][1])

    # Pagination: 24 products per page
    paginator = Paginator(queryset, 24)
    page_number = request.GET.get('page')
    
    try:
        page_obj = paginator.get_page(page_number)
    except (PageNotAnInteger, EmptyPage):
        page_obj = paginator.get_page(1)

    # Context items for sidebar filters
    # Count only published products, in one query, and skip categories with none
    categories = (
        Category.objects.filter(is_active=True)
        .annotate(published_count=Count('products', filter=Q(products__is_published=True)))
        .filter(published_count__gt=0)
        .order_by('display_order', 'name')
    )
    # Only brands with something to show in the catalogue
    brands = Brand.objects.filter(products__is_published=True).distinct().order_by('name')

    # Query strings for links that keep the current filters and sort
    params = {'q': query, 'category': category_slug if 'category' in active_filters else '',
              'brand': brand_slug if 'brand' in active_filters else '',
              'sort': sort if sort != DEFAULT_SORT else ''}

    def query_without(*names):
        return urlencode({k: v for k, v in params.items() if v and k not in names})

    # Page numbers to show: first, last and two either side of the current one (1 2 3 … 81)
    page_numbers = list(paginator.get_elided_page_range(page_obj.number, on_each_side=2, on_ends=1))

    context = {
        'page_obj': page_obj,
        'page_numbers': page_numbers,
        'ellipsis': Paginator.ELLIPSIS,
        'categories': categories,
        'brands': brands,
        'active_filters': active_filters,
        'sort_options': [(key, label) for key, (label, _) in SORT_OPTIONS.items()],
        'active_sort': sort,
        'page_query': query_without(),          # for pagination links: ?page=N&<page_query>
        'sort_query': query_without('q', 'category', 'brand'),  # keeps the sort on category/brand links
        'remove_filter_urls': {name: '?' + query_without(name) for name in ('q', 'category', 'brand')},
        # Keep search results and empty filter pages out of Google ("soft 404"); visitors still see them
        'robots_noindex': bool(query) or paginator.count == 0,
    }
    return render(request, 'catalogue/product_list.html', context)


@cache_public_page
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


@cache_public_page
def brand_list(request):
    # Count published products so brands with none yet show "coming soon" instead of an empty link
    brands = Brand.objects.annotate(
        published_count=Count('products', filter=Q(products__is_published=True))
    ).order_by('name')
    context = {
        'brands': brands
    }
    return render(request, 'catalogue/brand_list.html', context)


def category_detail_redirect(request, slug):
    # Redirect /categories/<slug>/ to products list page filtered by category
    return redirect(f'/products/?category={slug}', permanent=True)


def brand_detail_redirect(request, slug):
    # Redirect /brands/<slug>/ to products list page filtered by brand
    return redirect(f'/products/?brand={slug}', permanent=True)
