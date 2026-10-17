import os
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image

from catalogue.models import Brand, trim_logo_border


class Command(BaseCommand):
    help = "Trims empty space around existing brand logos so they display at a consistent size."

    def add_arguments(self, parser):
        parser.add_argument('--dry-run', action='store_true', help='Report what would change without writing files')

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        trimmed = skipped = 0

        for brand in Brand.objects.exclude(logo='').exclude(logo__isnull=True):
            storage, name = brand.logo.storage, brand.logo.name
            if not storage.exists(name):
                self.stdout.write(self.style.WARNING(f"{brand.name}: file missing ({name})"))
                skipped += 1
                continue

            with storage.open(name, 'rb') as f:
                original = Image.open(f)
                original.load()
            img, changed = trim_logo_border(original)
            if not changed:
                self.stdout.write(f"{brand.name}: already tight, skipped")
                skipped += 1
                continue

            self.stdout.write(f"{brand.name}: {original.width}x{original.height} -> {img.width}x{img.height}")
            trimmed += 1
            if dry_run:
                continue

            output = BytesIO()
            img.save(output, format='PNG', optimize=True)
            # A new file name means browsers fetch the trimmed logo instead of a cached copy
            saved_name = storage.save(f"{os.path.splitext(name)[0]}_trim.png", ContentFile(output.getvalue()))
            # Update the path without calling save(), which only handles fresh uploads
            Brand.objects.filter(pk=brand.pk).update(logo=saved_name)
            storage.delete(name)

        verb = 'Would trim' if dry_run else 'Trimmed'
        self.stdout.write(self.style.SUCCESS(f"{verb} {trimmed}; skipped {skipped}."))
