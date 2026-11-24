"""Template helpers for product cards."""
import re
from collections import Counter

from django import template

register = template.Library()

_CASE = re.compile(r'^\s*\d+\s*[x×]\s*', re.I)
_AMOUNT = re.compile(r'^\s*(\d+(?:\.\d+)?)\s*(kg|g|ltr|l|ml|lb)\b', re.I)
_TO_GRAMS = {'g': 1, 'kg': 1000, 'ml': 1, 'l': 1000, 'ltr': 1000, 'lb': 453.6}


@register.filter
def pack_choices(sizes):
    """Dropdown choices for a card: the pack weight only ("6 x 1 kg" -> "1 kg"), smallest first.

    The owner asked for just the weights. If two cases share the same weight
    (e.g. 10 x 100 g and 20 x 100 g), those keep the full case wording so the
    buyer can still tell them apart. Sizes that aren't a plain weight keep their order, last.
    """
    sizes = list(sizes)
    short = [_CASE.sub('', s.size, count=1).strip() or s.size for s in sizes]
    repeats = Counter(label.lower() for label in short)
    choices = []
    for index, (size, label) in enumerate(zip(sizes, short)):
        if repeats[label.lower()] > 1:
            label = size.size
        amount = _AMOUNT.match(_CASE.sub('', size.size, count=1))
        weight = float(amount.group(1)) * _TO_GRAMS[amount.group(2).lower()] if amount else None
        choices.append({'id': size.id, 'label': label,
                        'key': (weight is None, weight or 0, index)})
    return sorted(choices, key=lambda c: c['key'])


@register.filter
def logo_url(logo_field):
    """Small WebP copy of a brand logo when there is one (catalogue/logo_thumbs.py), else the original."""
    from catalogue.logo_thumbs import logo_url as _logo_url
    return _logo_url(logo_field)


@register.filter
def category_small_url(image_field):
    """Small phone copy of a category photo (catalogue/category_thumbs.py), or '' when there is none."""
    from catalogue.category_thumbs import small_url
    return small_url(image_field)
