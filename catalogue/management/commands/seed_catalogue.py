
import random
from django.core.management.base import BaseCommand
from django.utils.text import slugify
from catalogue.models import Category, Brand, Product, PackSize
from import_export.formats.base_formats import CSV
from catalogue.admin import ProductResource
import os

class Command(BaseCommand):
    help = "Seeds the database with initial products from the CSV and generates realistic B2B catalog data up to 480 items."

    def handle(self, *args, **options):
        self.stdout.write("Starting database seeding...")

        # 1. First import from products-import-template.csv if it exists
        csv_path = "products-import-template.csv"
        if os.path.exists(csv_path):
            self.stdout.write(f"Importing initial template products from {csv_path}...")
            resource = ProductResource()
            with open(csv_path, 'r', encoding='utf-8') as f:
                data = f.read()
            
            # Use import-export dataset representation
            dataset = CSV().create_dataset(data)
            result = resource.import_data(dataset, dry_run=False)
            
            self.stdout.write(self.style.SUCCESS(
                f"Successfully imported {result.totals['new']} new products from template CSV."
            ))
        else:
            self.stdout.write(self.style.WARNING("Template CSV file not found. Skipping template import."))

        # 2. Define categories, brands, and product name generators
        categories_data = {
            "Rice": ["Extra Long Basmati Rice", "Premium Sona Masoori Rice", "Classic Jasmine Rice", "Aged Ponni Rice", "Matta Red Rice", "Brown Basmati Rice", "Broken Basmati Rice", "Jeera Samba Rice", "Idli Rice", "Glutinous Rice"],
            "Spices": ["Ground Turmeric Powder", "Garam Masala Blend", "Mild Kashmiri Chili Powder", "Ground Cumin Seeds", "Coriander Powder", "Green Cardamom Pods", "Whole Cloves", "Cinnamon Sticks", "Black Mustard Seeds", "Fennel Seeds", "Fenugreek Seeds", "Whole Star Anise", "Black Peppercorns", "Ginger Powder", "Garlic Powder", "Crushed Red Chili Flakes", "Amchur Dry Mango Powder", "Asafoetida Hing", "Mace Whole", "Nutmeg Whole"],
            "Flour": ["Premium Chapatti Atta Flour", "Stoneground Wholewheat Atta", "Fine Gram Flour Besan", "Rice Flour White", "Ragi Finger Millet Flour", "Fine Semolina Sooji", "Coarse Semolina", "Maida All Purpose Flour", "Bajra Pearl Millet Flour", "Jowar Sorghum Flour"],
            "Oils": ["Cold Pressed Mustard Oil", "Pure Coconut Oil", "Filtered Groundnut Oil", "Refined Sunflower Oil", "Pure Cow Ghee", "Vanaspati Vegetable Ghee", "Sesame Til Oil", "Extra Virgin Olive Oil", "Canola Oil"],
            "Lentils": ["Split Toor Dal", "Split Chana Dal", "Split & Washed Urad Dal", "Split Red Masoor Dal", "Whole Moong Beans", "Split Moong Dal", "Whole Black Chickpeas", "Large Kabuli Chickpeas", "Red Kidney Beans Rajma", "Black Eyed Beans", "Green Peas Whole"],
            "Pickles": ["Spicy Mango Pickle", "Tangy Lime Pickle", "Mixed Vegetable Pickle", "Garlic Pickle in Oil", "Hot Green Chili Pickle", "Sweet Mango Chutney", "Gongura Red Sorrel Pickle", "Ginger Pickle", "Lemon Sweet Pickle"]
        }

        brands_data = ["Indus Valley", "Royal Harvest", "Desi Kitchen", "Pantry Gold", "Bristol Spices", "Southern Delights"]
        
        # Ensure categories exist
        category_objects = {}
        for cat_name in categories_data.keys():
            cat_obj, created = Category.objects.get_or_create(
                name=cat_name,
                defaults={'slug': slugify(cat_name), 'display_order': len(category_objects) * 10}
            )
            category_objects[cat_name] = cat_obj

        # Ensure brands exist
        brand_objects = []
        for brand_name in brands_data:
            brand_obj, created = Brand.objects.get_or_create(
                name=brand_name,
                defaults={'slug': slugify(brand_name), 'is_featured': random.choice([True, False])}
            )
            brand_objects.append(brand_obj)

        # Generate realistic items to make up 480 products
        current_count = Product.objects.count()
        target_count = 480
        
        if current_count >= target_count:
            self.stdout.write(self.style.SUCCESS(
                f"Database already has {current_count} products. No generation needed."
            ))
            return

        needed = target_count - current_count
        self.stdout.write(f"Generating {needed} realistic products to reach the 480 target...")

        # Common package size combinations
        pack_size_options = {
            "Rice": ["5kg|10kg|20kg", "10kg|20kg", "20kg"],
            "Spices": ["100g|400g|1kg|5kg", "400g|1kg|5kg", "1kg|5kg"],
            "Flour": ["5kg|10kg|20kg", "10kg|20kg"],
            "Oils": ["1L|5L|15L", "5L|15L", "15L"],
            "Lentils": ["1kg|5kg|10kg|20kg", "5kg|10kg|20kg"],
            "Pickles": ["400g|1kg|5kg", "1kg|5kg"]
        }

        generated = 0
        while generated < needed:
            # Pick a random category
            cat_name = random.choice(list(categories_data.keys()))
            category = category_objects[cat_name]
            
            # Make SKU unique by adding a suffix
            sku_suffix = random.randint(1000, 9999)
            sku = f"SP-{cat_name[:4].upper()}-{sku_suffix:04d}"
            
            # Check if SKU already exists
            if Product.objects.filter(sku=sku).exists():
                continue
            
            # Generate a name
            base_name = random.choice(categories_data[cat_name])
            brand = random.choice(brand_objects)
            product_name = f"{brand.name} {base_name}"
            
            # If name collision occurs, append SKU to make it unique
            if Product.objects.filter(name=product_name).exists():
                product_name = f"{brand.name} {base_name} ({sku})"
                
            if Product.objects.filter(name=product_name).exists():
                continue
                
            slug = slugify(product_name)
            
            # Mock descriptions and specifications
            description = f"Premium quality {product_name.lower()} sourced directly from select producers. Carefully packed and stored to maintain maximum freshness and flavor profile. Suitable for high-volume commercial kitchens, restaurants, and retail distribution."
            origin = random.choice(["India", "United Kingdom", "Vietnam", "Thailand", "Spain", "Italy"])
            storage = "Store in a cool, dry place. Keep container tightly sealed after opening."
            packaging = random.choice(["Heavy-duty woven polypropylene sack", "Food-grade sealed laminate pouch", "Corrugated catering carton", "High-density plastic jerry can"])
            ingredients = f"100% {base_name.lower()}"
            
            # Badges
            badge = random.choice(["Best Seller", "New", "Featured", "", ""])
            
            # Create product
            product = Product.objects.create(
                name=product_name,
                slug=slug,
                sku=sku,
                category=category,
                brand=brand,
                description=description,
                country_of_origin=origin,
                ingredients=ingredients,
                storage_info=storage,
                packaging_info=packaging,
                is_published=True,
                is_featured=random.choice([True, False, False, False]),
                badge=badge,
                meta_title=f"Wholesale {product_name} Supplier Bristol | Spice Pantry",
                meta_description=f"Purchase bulk wholesale {product_name.lower()} from Spice Pantry. High quality catering sizes for Bristol food businesses."
            )
            
            # Add pack sizes
            sizes_str = random.choice(pack_size_options[cat_name])
            sizes = [s.strip() for s in sizes_str.split('|')]
            for idx, size_val in enumerate(sizes):
                PackSize.objects.create(
                    product=product,
                    size=size_val,
                    display_order=idx
                )
                
            generated += 1

        self.stdout.write(self.style.SUCCESS(
            f"Successfully seeded database. Total products in database: {Product.objects.count()}."
        ))
