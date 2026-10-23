from django.contrib import admin
from django.urls import path, include, re_path
from django.views.static import serve
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse
from django.urls import reverse
from django.contrib.sitemaps.views import sitemap

from catalogue.sitemaps import ProductSitemap, CategorySitemap, BrandSitemap, StaticViewSitemap

sitemaps = {
    'products': ProductSitemap,
    'categories': CategorySitemap,
    'brands': BrandSitemap,
    'static': StaticViewSitemap,
}

def robots_txt(request):
    lines = [
        "User-agent: *",
        # The real admin path is deliberately not listed: robots.txt is public
        "Disallow: /admin/",
        # Built from the request, so it always names the domain the site is served from
        f"Sitemap: {request.build_absolute_uri(reverse('django.contrib.sitemaps.views.sitemap'))}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")

# Admin Branding
admin.site.site_header = "Spice Pantry Admin Portal"
admin.site.site_title = "Spice Pantry"
admin.site.index_title = "Wholesale Catalogue & Operations Management"

urlpatterns = [
    # Custom non-obvious URL path for the admin
    path(f'{settings.ADMIN_URL_PATH}/', admin.site.urls),
    
    # robots.txt and sitemaps.xml
    path('robots.txt', robots_txt, name='robots_txt'),
    path('sitemap.xml', sitemap, {'sitemaps': sitemaps}, name='django.contrib.sitemaps.views.sitemap'),

    # Include App URLs
    path('', include('pages.urls')),
    path('', include('catalogue.urls')),
    path('', include('enquiries.urls')),
]

# Serve media files in development, and in the temporary ngrok preview (config.settings.preview)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
elif getattr(settings, 'PREVIEW_SERVE_MEDIA', False):
    urlpatterns += [
        re_path(r'^media/(?P<path>.*)$', serve, {'document_root': settings.MEDIA_ROOT}),
    ]
