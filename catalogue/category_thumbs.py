"""Small phone copies of the home-page category photos (24 Nov 2026).

The category circles are 400 x 400 WebP pictures (about 37 KB each), but on a phone each circle is
only about 115 px wide. A 240 px copy (sharp on 2x phone screens, about 15 KB) is kept next to the
original in media/categories/thumbs/ and offered to browsers through srcset; computers and
high-density tablets still get the original. The uploaded original is never changed.
"""
import os
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from PIL import Image

SIZE = 240


def thumb_name(image_name):
    stem = os.path.splitext(os.path.basename(image_name))[0]
    return f'categories/thumbs/{stem}-{SIZE}.webp'


def make_thumb(image_field):
    """Write (or rewrite) the small WebP copy of a category photo. Returns the stored name, or None."""
    if not image_field:
        return None
    with default_storage.open(image_field.name, 'rb') as f:
        img = Image.open(f)
        img.load()
    img = img.convert('RGBA') if img.mode in ('P', 'LA', 'RGBA') or 'transparency' in img.info else img.convert('RGB')
    img.thumbnail((SIZE, SIZE), Image.LANCZOS)
    out = BytesIO()
    img.save(out, format='WEBP', quality=82, method=6)
    name = thumb_name(image_field.name)
    if default_storage.exists(name):
        default_storage.delete(name)
    return default_storage.save(name, ContentFile(out.getvalue()))


def small_url(image_field):
    """URL of the small copy, or '' when there is none (the page then simply uses the original)."""
    if not image_field:
        return ''
    name = thumb_name(image_field.name)
    try:
        if default_storage.exists(name):
            return default_storage.url(name)
    except Exception:
        pass
    return ''
