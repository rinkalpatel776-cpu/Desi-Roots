"""Small web versions of brand logos (21 Nov 2026).

Logos are uploaded as large PNGs (up to ~900 KB) but shown at about 110 px. A WebP copy at most
320 px on its longest side (sharp on 3x phone screens) is kept next to the original in
media/brands/thumbs/ and used on the website. The uploaded original is never changed.
"""
import os
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image

MAX_SIDE = 320


def thumb_name(logo_name):
    stem = os.path.splitext(os.path.basename(logo_name))[0]
    return f'brands/thumbs/{stem}.webp'


def make_thumb(logo_field):
    """Write (or rewrite) the small WebP copy of a logo. Returns the stored name, or None."""
    if not logo_field:
        return None
    with default_storage.open(logo_field.name, 'rb') as f:
        img = Image.open(f)
        img.load()
    img = img.convert('RGBA') if img.mode in ('P', 'LA', 'RGBA') or 'transparency' in img.info else img.convert('RGB')
    img.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
    out = BytesIO()
    img.save(out, format='WEBP', quality=88, method=6)
    name = thumb_name(logo_field.name)
    if default_storage.exists(name):
        default_storage.delete(name)
    return default_storage.save(name, ContentFile(out.getvalue()))


def logo_url(logo_field):
    """URL of the small copy when it exists, otherwise the original (so a missing copy never breaks a page)."""
    if not logo_field:
        return ''
    name = thumb_name(logo_field.name)
    try:
        if default_storage.exists(name):
            return default_storage.url(name)
    except Exception:
        pass
    return logo_field.url
