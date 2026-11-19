"""Whole-page cache for the public pages (20 Nov 2026).

Pages are kept in Django's file cache, which all Gunicorn workers share, for
PAGE_CACHE_SECONDS. Any change saved to a catalogue, page or site-settings model
(in the admin or an import) changes the "page version" at once, so every worker
stops serving the old copies immediately. Searches, staff visitors, non-GET
requests and responses that set cookies are never cached.
"""
import functools
import uuid

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.db.models.signals import post_delete, post_save

VERSION_KEY = 'page-cache-version'
# Models whose changes show up on public pages
WATCHED_APPS = {'catalogue', 'pages', 'core'}
# Other cached fragments that must refresh with the pages
RELATED_KEYS = ('footer_categories',)


def current_version():
    version = cache.get(VERSION_KEY)
    if version is None:
        version = uuid.uuid4().hex
        cache.add(VERSION_KEY, version, None)
        version = cache.get(VERSION_KEY, version)
    return version


def bump_version(**_kwargs):
    """Mark every cached page as out of date (all workers see it: the cache is shared)."""
    cache.set(VERSION_KEY, uuid.uuid4().hex, None)
    cache.delete_many(RELATED_KEYS)


def _on_model_change(sender, **kwargs):
    if sender._meta.app_label in WATCHED_APPS:
        # After the change is committed: refreshing earlier could let a visitor's request,
        # still seeing the old data, save an old page under the new version.
        transaction.on_commit(bump_version)


def connect_signals():
    post_save.connect(_on_model_change, dispatch_uid='page_cache_post_save')
    post_delete.connect(_on_model_change, dispatch_uid='page_cache_post_delete')


def _key(request):
    scheme = 'https' if request.is_secure() else 'http'
    return f'page:{current_version()}:{scheme}://{request.get_host()}{request.get_full_path()}'


def cache_public_page(view):
    """Serve a saved copy of a public page when one is fresh; otherwise build it and save it."""
    @functools.wraps(view)
    def wrapper(request, *args, **kwargs):
        seconds = getattr(settings, 'PAGE_CACHE_SECONDS', 0)
        cacheable = (
            seconds > 0
            and request.method in ('GET', 'HEAD')
            and 'q' not in request.GET            # search results: too many variations
            and not request.user.is_authenticated
        )
        if not cacheable:
            return view(request, *args, **kwargs)
        key = _key(request)
        cached = cache.get(key)
        if cached is not None:
            cached['X-Page-Cache'] = 'hit'
            return cached
        response = view(request, *args, **kwargs)
        uses_csrf = request.META.get('CSRF_COOKIE_NEEDS_UPDATE') or request.META.get('CSRF_COOKIE_USED')
        if response.status_code == 200 and not response.cookies and not uses_csrf and not getattr(response, 'streaming', False):
            if hasattr(response, 'render') and callable(response.render):
                response.render()
            cache.set(key, response, seconds)
        response['X-Page-Cache'] = 'miss'
        return response
    return wrapper
