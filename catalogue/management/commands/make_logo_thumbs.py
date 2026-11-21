"""Make the small web copies of every brand logo (run once after deploying; new uploads get one automatically)."""
from django.core.management.base import BaseCommand

from catalogue.logo_thumbs import make_thumb
from catalogue.models import Brand


class Command(BaseCommand):
    help = "Create small WebP copies of brand logos in media/brands/thumbs/ (originals are not changed)."

    def handle(self, *args, **options):
        made = 0
        for brand in Brand.objects.exclude(logo='').exclude(logo__isnull=True):
            try:
                make_thumb(brand.logo)
                made += 1
            except Exception as exc:  # a missing or broken file must not stop the others
                self.stderr.write(f"{brand.name}: {exc}")
        self.stdout.write(f"Made {made} logo copies.")
