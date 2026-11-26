"""Structured data (JSON-LD) for Google and AI answer engines (23 Nov 2026).

Built with json.dumps so every value is correctly escaped (the old hand-written block put
HTML-escaped text inside JSON). Contact details come from Site Settings only.
Deliberately no street address: the registered office is a home address, so only the city is given.
"""
import json

from django import template
from django.templatetags.static import static
from django.utils.safestring import mark_safe

register = template.Library()

# Areas named on the site itself (contact page: "Bristol, Bath and nearby areas")
AREAS_SERVED = ['Bristol', 'Bath', 'South West England']


def _render(data):
    # "<" escaped so text can never close the <script> tag early
    text = json.dumps(data, ensure_ascii=False, indent=1).replace('<', '\\u003c')
    return mark_safe(f'<script type="application/ld+json">\n{text}\n</script>')


def _origin(request):
    return f'{request.scheme}://{request.get_host()}'


@register.simple_tag(takes_context=True)
def site_schema(context):
    request = context['request']
    settings = context.get('site_settings')
    origin = _origin(request)
    business = {
        '@type': ['Organization', 'WholesaleStore'],
        '@id': f'{origin}/#business',
        'name': 'Desi Roots',
        'legalName': 'Desi Roots Ltd',
        'url': f'{origin}/',
        'logo': origin + static('images/logo-400.webp'),
        'image': origin + static('images/og-share.jpg'),
        'description': ('Wholesale spices, lentils, rice, flour and ethnic groceries for restaurants, '
                        'takeaways, caterers and shops in Bristol and nearby areas.'),
        'address': {'@type': 'PostalAddress', 'addressLocality': 'Bristol', 'addressCountry': 'GB'},
        'areaServed': AREAS_SERVED,
    }
    if settings is not None:
        if getattr(settings, 'vat_number', ''):
            business['vatID'] = settings.vat_number.replace(' ', '')
        if getattr(settings, 'phone_number', ''):
            business['telephone'] = settings.phone_number
        if getattr(settings, 'email_address', ''):
            business['email'] = settings.email_address
        contact = {'@type': 'ContactPoint', 'contactType': 'sales', 'areaServed': 'GB', 'availableLanguage': 'en'}
        if getattr(settings, 'phone_number', ''):
            contact['telephone'] = settings.phone_number
        if getattr(settings, 'email_address', ''):
            contact['email'] = settings.email_address
        business['contactPoint'] = [contact]
        profiles = [getattr(settings, f, '') for f in ('facebook_url', 'instagram_url', 'linkedin_url')]
        profiles = [p for p in profiles if p]
        if profiles:
            business['sameAs'] = profiles
    website = {
        '@type': 'WebSite',
        '@id': f'{origin}/#website',
        'url': f'{origin}/',
        'name': 'Desi Roots',
        'publisher': {'@id': f'{origin}/#business'},
        'inLanguage': 'en-GB',
        'potentialAction': {
            '@type': 'SearchAction',
            'target': {'@type': 'EntryPoint', 'urlTemplate': f'{origin}/products/?q={{search_term_string}}'},
            'query-input': 'required name=search_term_string',
        },
    }
    return _render({'@context': 'https://schema.org', '@graph': [business, website]})


@register.simple_tag(takes_context=True)
def breadcrumb_schema(context, *pairs):
    """{% breadcrumb_schema "Products" "/products/" %}: Home is added first."""
    origin = _origin(context['request'])
    items = [('Home', '/')] + [(pairs[i], pairs[i + 1]) for i in range(0, len(pairs) - 1, 2)]
    return _render({
        '@context': 'https://schema.org', '@type': 'BreadcrumbList',
        'itemListElement': [{'@type': 'ListItem', 'position': n, 'name': name, 'item': origin + path}
                            for n, (name, path) in enumerate(items, start=1)],
    })


@register.simple_tag
def faq_schema(faqs):
    """FAQPage markup, only when there are real answers (nothing is output for an empty list)."""
    faqs = list(faqs)
    if not faqs:
        return ''
    return _render({
        '@context': 'https://schema.org', '@type': 'FAQPage',
        'mainEntity': [{'@type': 'Question', 'name': f.question,
                        'acceptedAnswer': {'@type': 'Answer', 'text': f.answer}} for f in faqs],
    })


# Query parameters that make a genuinely different page. Everything else (search, sort,
# utm_*/fbclid tracking, page=1) points back at the clean page, so Google sees one main copy.
CANONICAL_PARAMS = ('category', 'brand', 'page')


@register.simple_tag(takes_context=True)
def canonical_url(context):
    from urllib.parse import urlencode
    request = context['request']
    host = request.get_host()
    if host.startswith('www.'):
        host = host[4:]
    keep = []
    # Only the catalogue listing has real filter/page variants; every other page is one clean URL
    for name in (CANONICAL_PARAMS if request.path == '/products/' else ()):
        value = request.GET.get(name, '').strip()
        if not value or (name == 'page' and (not value.isdigit() or int(value) <= 1)):
            continue
        keep.append((name, value))
    query = ('?' + urlencode(keep)) if keep else ''
    return f'{request.scheme}://{host}{request.path}{query}'
