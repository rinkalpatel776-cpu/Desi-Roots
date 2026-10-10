import os
from django.core.management.base import BaseCommand
from import_export.formats.base_formats import CSV
from catalogue.admin import ProductResource
from catalogue.models import Product

class Command(BaseCommand):
    help = "Imports products from a CSV file into the database using django-import-export."

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='products-import-template.csv',
            help='Path to the products CSV file to import (default: products-import-template.csv)'
        )

    def handle(self, *args, **options):
        csv_path = options['file']
        self.stdout.write(f"Starting catalogue import from {csv_path}...")

        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f"File not found: {csv_path}"))
            return

        resource = ProductResource()
        with open(csv_path, 'r', encoding='utf-8') as f:
            data = f.read()

        dataset = CSV().create_dataset(data)
        result = resource.import_data(dataset, dry_run=False)

        if result.has_errors():
            self.stdout.write(self.style.ERROR("Import encountered errors:"))
            for error in result.base_errors:
                self.stdout.write(self.style.ERROR(str(error.error)))
            for line, errors in result.row_errors():
                for error in errors:
                    self.stdout.write(self.style.ERROR(f"Line {line}: {error.error}"))
        else:
            self.stdout.write(self.style.SUCCESS(
                f"Import complete! New: {result.totals.get('new', 0)}, "
                f"Updated: {result.totals.get('update', 0)}, "
                f"Skipped: {result.totals.get('skip', 0)}. "
                f"Total published products in database: {Product.objects.filter(is_published=True).count()}."
            ))
