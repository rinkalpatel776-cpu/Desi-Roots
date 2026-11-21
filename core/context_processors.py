from .models import SiteSettings

def site_settings(request):
    try:
        settings = SiteSettings.objects.first()
    except Exception:
        settings = None

    if not settings:
        # Return an unsaved default instance so properties are accessible but empty
        settings = SiteSettings()

    return {
        'site_settings': settings
    }


FOOTER_CATEGORY_LIMIT = 6


def footer_categories(request):
    """The footer's Catalogue links: the categories with the most published products (cached 10 minutes)."""
    from django.core.cache import cache
    from django.db.models import Count, Q
    from catalogue.models import Category

    def load():
        return list(
            Category.objects.filter(is_active=True)
            .annotate(published_count=Count('products', filter=Q(products__is_published=True)))
            .filter(published_count__gt=0)
            .order_by('-published_count', 'name')
            .values('name', 'slug')[:FOOTER_CATEGORY_LIMIT]
        )

    try:
        categories = cache.get_or_set('footer_categories', load, 600)
    except Exception:
        categories = []
    return {'footer_categories': categories}


def has_faqs(request):
    """True once the owner has added at least one active FAQ; until then FAQ is left out of the menu and footer."""
    from pages.models import FAQ
    try:
        return {'has_faqs': FAQ.objects.filter(is_active=True).exists()}
    except Exception:
        return {'has_faqs': False}


def analytics(request):
    """Google Analytics ID for the cookie pop-up; empty (off) for signed-in staff so their visits are not counted."""
    from django.conf import settings
    ga_id = getattr(settings, 'GA_MEASUREMENT_ID', '')
    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated:
        ga_id = ''
    return {'ga_measurement_id': ga_id}
