"""Make the small phone copies of every category photo (run once after deploying; new uploads get one automatically)."""
from django.core.management.base import BaseCommand

from catalogue.category_thumbs import make_thumb
from catalogue.models import Category


class Command(BaseCommand):
    help = "Create small WebP copies of category photos in media/categories/thumbs/ (originals are not changed)."

    def handle(self, *args, **options):
        made = 0
        for category in Category.objects.exclude(image='').exclude(image__isnull=True):
            try:
                make_thumb(category.image)
                made += 1
            except Exception as exc:  # a missing or broken file must not stop the others
                self.stderr.write(f"{category.name}: {exc}")
        self.stdout.write(f"Made {made} category photo copies.")
