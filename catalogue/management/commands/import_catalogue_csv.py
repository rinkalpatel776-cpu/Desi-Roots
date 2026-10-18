import csv
import os

from django.core.files import File
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.text import slugify

from catalogue.models import Brand, Category, PackSize, Product, ProductImage


class DryRun(Exception):
    pass


class Command(BaseCommand):
    help = (
        "Imports the supplier catalogue review spreadsheet: one row per product, pipe-separated "
        "pack_sizes with matching pack_size_skus, and an optional photo per product. "
        "New products are created as drafts. Safe to re-run."
    )

    def add_arguments(self, parser):
        parser.add_argument('csv_path', help='Path to the review spreadsheet (CSV)')
        parser.add_argument('--photos', default='', help='Folder holding the files named in image_filename')
        parser.add_argument('--dry-run', action='store_true', help='Show what would change, then roll back')

    def handle(self, *args, **options):
        path, photos_dir = options['csv_path'], options['photos']
        if not os.path.exists(path):
            raise CommandError(f"File not found: {path}")

        with open(path, encoding='utf-8-sig', newline='') as f:
            rows = list(csv.DictReader(f))
        missing = {'name', 'brand', 'category', 'pack_sizes'} - set(rows[0].keys() if rows else [])
        if missing:
            raise CommandError(f"Missing columns: {', '.join(sorted(missing))}")

        self.stats = {'created': 0, 'updated': 0, 'pack_sizes': 0, 'photos': 0, 'photo_missing': 0,
                      'brands_created': 0, 'categories_created': 0}
        self.brands, self.categories = {}, {}
        self.dry_run = options['dry_run']
        try:
            with transaction.atomic():
                for row in rows:
                    self.import_row(row, photos_dir)
                if options['dry_run']:
                    raise DryRun
        except DryRun:
            self.stdout.write(self.style.WARNING("Dry run: nothing was saved."))

        s = self.stats
        self.stdout.write(self.style.SUCCESS(
            f"Products created: {s['created']}, updated: {s['updated']} | pack sizes: {s['pack_sizes']} | "
            f"photos attached: {s['photos']}, photo file not found: {s['photo_missing']} | "
            f"new brands: {s['brands_created']}, new categories: {s['categories_created']}"
        ))

    def get_brand(self, name):
        name = name.strip()
        if not name:
            return None
        if name not in self.brands:
            brand = Brand.objects.filter(name__iexact=name).first() or Brand.objects.filter(slug=slugify(name)).first()
            if not brand:
                brand = Brand.objects.create(name=name, slug=slugify(name))
                self.stats['brands_created'] += 1
            self.brands[name] = brand
        return self.brands[name]

    def get_category(self, name):
        name = name.strip() or 'Other Provisions'
        if name not in self.categories:
            cat = Category.objects.filter(name__iexact=name).first() or Category.objects.filter(slug=slugify(name)).first()
            if not cat:
                cat = Category.objects.create(name=name, slug=slugify(name))
                self.stats['categories_created'] += 1
            self.categories[name] = cat
        return self.categories[name]

    def unique_slug(self, name, product):
        base = slugify(name)[:230] or 'product'
        slug, n = base, 2
        while Product.objects.filter(slug=slug).exclude(pk=product.pk).exists():
            slug, n = f"{base}-{n}", n + 1
        return slug

    def import_row(self, row, photos_dir):
        name = row['name'].strip()
        sku = (row.get('sku') or '').strip() or None
        slug = slugify(name)[:230]
        product = (Product.objects.filter(sku=sku).first() if sku
                   else Product.objects.filter(sku__isnull=True, slug=slug).first())
        created = product is None
        if created:
            product = Product(is_published=False)
        product.name, product.sku = name, sku
        product.brand = self.get_brand(row['brand'])
        product.category = self.get_category(row['category'])
        if created or not product.slug:
            product.slug = self.unique_slug(name, product)
        product.save()
        self.stats['created' if created else 'updated'] += 1

        sizes = [s.strip() for s in row['pack_sizes'].split('|') if s.strip()]
        codes = [c.strip() for c in (row.get('pack_size_skus') or '').split('|')]
        product.pack_sizes.all().delete()
        PackSize.objects.bulk_create([
            PackSize(product=product, size=size, sku=codes[i] if i < len(codes) else '', display_order=i)
            for i, size in enumerate(sizes)
        ])
        self.stats['pack_sizes'] += len(sizes)

        filename = (row.get('image_filename') or '').strip()
        if filename and not product.images.exists():
            photo_path = os.path.join(photos_dir, os.path.basename(filename))
            if not os.path.exists(photo_path):
                self.stats['photo_missing'] += 1
                return
            if self.dry_run:  # rolling back the database would not remove written files
                self.stats['photos'] += 1
                return
            with open(photo_path, 'rb') as fh:
                ProductImage(product=product, alt_text=name, is_primary=True,
                             image=File(fh, name=os.path.basename(filename))).save()
            self.stats['photos'] += 1
