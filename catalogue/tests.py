
import os
import csv
from django.test import TestCase, Client
from django.utils.text import slugify
from .models import Category, Brand, Product, PackSize, ProductImage

class CatalogueTests(TestCase):
    def setUp(self):
        self.client = Client()
        
        # Create Category
        self.category = Category.objects.create(
            name="Rice",
            slug="rice",
            display_order=10
        )
        self.inactive_category = Category.objects.create(
            name="Inactive Cat",
            slug="inactive-cat",
            is_active=False
        )

        # Create Brand
        self.brand = Brand.objects.create(
            name="Indus Valley",
            slug="indus-valley",
            is_featured=True
        )

        # Create Products
        self.product_published = Product.objects.create(
            name="Premium Basmati Rice",
            slug="premium-basmati-rice",
            sku="SP-RICE-101",
            category=self.category,
            brand=self.brand,
            description="Premium quality aged basmati rice.",
            is_published=True
        )
        PackSize.objects.create(product=self.product_published, size="5kg", display_order=0)
        PackSize.objects.create(product=self.product_published, size="10kg", display_order=1)

        self.product_unpublished = Product.objects.create(
            name="Secret Rice",
            slug="secret-rice",
            sku="SP-RICE-102",
            category=self.category,
            brand=self.brand,
            is_published=False
        )

    def test_catalogue_rendering_and_pagination(self):
        # Request all products listing page
        response = self.client.get('/products/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Premium Basmati Rice")
        self.assertNotContains(response, "Secret Rice")

    def test_search_functionality(self):
        # Search by query "basmati"
        response = self.client.get('/products/?q=basmati')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Premium Basmati Rice")
        
        # Search by non-existent query
        response = self.client.get('/products/?q=nonexistent')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No Products Found")

    def test_filtering_functionality(self):
        # Filter by category "rice"
        response = self.client.get('/products/?category=rice')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Premium Basmati Rice")

        # Filter by brand "indus-valley"
        response = self.client.get('/products/?brand=indus-valley')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Premium Basmati Rice")

    def test_detail_page_access(self):
        # Published product detail page
        response = self.client.get('/products/premium-basmati-rice/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Premium Basmati Rice")
        self.assertContains(response, "5kg")
        self.assertContains(response, "10kg")

        # Unpublished product detail page should return 404
        response = self.client.get('/products/secret-rice/')
        self.assertEqual(response.status_code, 404)

    def test_sitemap_xml(self):
        # Sitemap loading
        response = self.client.get('/sitemap.xml')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "premium-basmati-rice")

    def test_robots_txt(self):
        # Robots.txt loading
        response = self.client.get('/robots.txt')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "User-agent")
        self.assertContains(response, "Sitemap")

    def test_product_image_optimization(self):
        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image
        import io
        import os
        from .models import ProductImage
        
        # Create a large test image in memory (e.g. 1000x800)
        file_obj = io.BytesIO()
        image = Image.new('RGB', size=(1000, 800), color=(201, 138, 43))
        image.save(file_obj, 'jpeg')
        file_obj.seek(0)
        
        uploaded_file = SimpleUploadedFile(
            "large_product.jpg", 
            file_obj.read(), 
            content_type="image/jpeg"
        )
        
        # Save ProductImage instance
        product_image = ProductImage.objects.create(
            product=self.product_published,
            image=uploaded_file,
            alt_text="Optimized image test",
            is_primary=True
        )
        
        try:
            # Check that the image was resized and thumbnail was generated
            self.assertTrue(product_image.image)
            self.assertTrue(product_image.thumbnail)
            
            # Open and inspect saved files using Pillow
            saved_img = Image.open(product_image.image.path)
            self.assertLessEqual(saved_img.width, 800)
            self.assertLessEqual(saved_img.height, 600)
            
            saved_thumb = Image.open(product_image.thumbnail.path)
            self.assertLessEqual(saved_thumb.width, 300)
            self.assertLessEqual(saved_thumb.height, 225)
        finally:
            # Cleanup files from disk after testing
            try:
                if product_image.image and os.path.exists(product_image.image.path):
                    os.remove(product_image.image.path)
                if product_image.thumbnail and os.path.exists(product_image.thumbnail.path):
                    os.remove(product_image.thumbnail.path)
            except Exception:
                pass


from import_export.formats.base_formats import CSV
from .admin import ProductResource

class ProductResourceImportTests(TestCase):
    def setUp(self):
        # Existing DB brands with uppercase names
        self.brand_east_end = Brand.objects.create(name="EAST END", slug="east-end")
        self.brand_fudco = Brand.objects.create(name="FUDCO", slug="fudco")
        self.brand_trs = Brand.objects.create(name="TRS", slug="trs")
        self.category_rice = Category.objects.create(name="Rice", slug="rice")
        self.resource = ProductResource()

    def test_case_insensitive_brand_matching_and_reuse(self):
        csv_data = """sku,name,category,brand,is_published,is_featured,pack_sizes
E043309,Ground Rice,Rice,East End,FALSE,FALSE,5 kg|1.5 kg
F050959,Pawa Rice Flakes,Rice,Fudco,FALSE,FALSE,1 kg
T038692,Basmati Rice,Rice,TRS,FALSE,FALSE,5 kg
"""
        dataset = CSV().create_dataset(csv_data)
        result = self.resource.import_data(dataset, dry_run=False)
        self.assertFalse(result.has_errors())
        self.assertEqual(result.totals['new'], 3)

        # Confirm no duplicate brands were created
        self.assertEqual(Brand.objects.count(), 3)
        
        # Verify foreign keys attached to existing brand records
        p1 = Product.objects.get(sku="E043309")
        self.assertEqual(p1.brand, self.brand_east_end)
        self.assertEqual(p1.name, "Ground Rice")
        self.assertFalse(p1.is_published)
        self.assertFalse(p1.is_featured)
        self.assertEqual(p1.pack_sizes.count(), 2)

        p2 = Product.objects.get(sku="F050959")
        self.assertEqual(p2.brand, self.brand_fudco)

        p3 = Product.objects.get(sku="T038692")
        self.assertEqual(p3.brand, self.brand_trs)

    def test_genuinely_new_brand_creation(self):
        csv_data = """sku,name,category,brand,is_published,is_featured
NEW-001,Special Lentils,Lentils,Heera,FALSE,FALSE
"""
        dataset = CSV().create_dataset(csv_data)
        result = self.resource.import_data(dataset, dry_run=False)
        self.assertFalse(result.has_errors())
        self.assertEqual(result.totals['new'], 1)

        # Brand Heera should be created
        heera = Brand.objects.get(slug="heera")
        self.assertEqual(heera.name, "Heera")
        self.assertEqual(Brand.objects.count(), 4)

    def test_repeated_imports_do_not_duplicate_products_or_brands(self):
        csv_data = """sku,name,category,brand,is_published,is_featured
E043309,Ground Rice,Rice,East End,FALSE,FALSE
"""
        dataset = CSV().create_dataset(csv_data)
        
        # First import
        result1 = self.resource.import_data(dataset, dry_run=False)
        self.assertEqual(result1.totals['new'], 1)
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(Brand.objects.count(), 3)

        # Second import of same SKU
        result2 = self.resource.import_data(dataset, dry_run=False)
        self.assertFalse(result2.has_errors())
        self.assertEqual(Product.objects.count(), 1)
        self.assertEqual(Brand.objects.count(), 3)

    def tearDown(self):
        import os
        from django.conf import settings
        products_dir = os.path.join(settings.MEDIA_ROOT, 'products')
        if os.path.exists(products_dir):
            for f in os.listdir(products_dir):
                if f.startswith('test_img_'):
                    p = os.path.join(products_dir, f)
                    if os.path.isfile(p):
                        os.remove(p)
        thumb_dir = os.path.join(settings.MEDIA_ROOT, 'products', 'thumbnails')
        if os.path.exists(thumb_dir):
            for f in os.listdir(thumb_dir):
                if f.startswith('test_img_'):
                    p = os.path.join(thumb_dir, f)
                    if os.path.isfile(p):
                        os.remove(p)

    def _create_media_file(self, filename):
        import os
        from django.conf import settings
        from PIL import Image as PilImage
        products_dir = os.path.join(settings.MEDIA_ROOT, 'products')
        os.makedirs(products_dir, exist_ok=True)
        file_path = os.path.join(products_dir, filename)
        PilImage.new('RGB', (400, 300), color='gold').save(file_path)
        return file_path

    def test_image_successful_linking(self):
        self._create_media_file('test_img_turmeric.jpg')
        csv_data = """sku,name,category,brand,is_published,is_featured,image_filename
E043309,Ground Rice,Rice,East End,FALSE,FALSE,test_img_turmeric.jpg
"""
        dataset = CSV().create_dataset(csv_data)
        result = self.resource.import_data(dataset, dry_run=False)
        self.assertFalse(result.has_errors())

        product = Product.objects.get(sku="E043309")
        self.assertEqual(product.images.count(), 1)
        img = product.images.first()
        self.assertEqual(img.image.name, "products/test_img_turmeric.jpg")
        self.assertTrue(img.is_primary)
        self.assertTrue(img.thumbnail.name.startswith("products/thumbnails/"))

        report = self.resource.get_image_report()
        self.assertEqual(report['total_linked'], 1)
        self.assertEqual(report['total_missing'], 0)

    def test_image_missing_file_handling(self):
        # File test_img_nonexistent.jpg is NOT created on disk
        csv_data = """sku,name,category,brand,is_published,is_featured,image_filename
E043309,Ground Rice,Rice,East End,FALSE,FALSE,test_img_nonexistent.jpg
"""
        dataset = CSV().create_dataset(csv_data)
        result = self.resource.import_data(dataset, dry_run=False)
        self.assertFalse(result.has_errors())

        product = Product.objects.get(sku="E043309")
        self.assertEqual(product.images.count(), 0)

        report = self.resource.get_image_report()
        self.assertEqual(report['total_linked'], 0)
        self.assertEqual(report['total_missing'], 1)
        self.assertEqual(report['missing'][0], ("E043309", "test_img_nonexistent.jpg"))

    def test_image_repeated_import_prevents_duplicates(self):
        self._create_media_file('test_img_repeat.jpg')
        csv_data = """sku,name,category,brand,is_published,is_featured,image_filename
E043309,Ground Rice,Rice,East End,FALSE,FALSE,test_img_repeat.jpg
"""
        dataset = CSV().create_dataset(csv_data)
        
        # First import
        result1 = self.resource.import_data(dataset, dry_run=False)
        self.assertFalse(result1.has_errors())
        product = Product.objects.get(sku="E043309")
        self.assertEqual(product.images.count(), 1)

        # Second import with same image
        result2 = self.resource.import_data(dataset, dry_run=False)
        self.assertFalse(result2.has_errors())
        self.assertEqual(product.images.count(), 1)

        report = self.resource.get_image_report()
        self.assertEqual(report['total_skipped'], 1)
        self.assertEqual(report['skipped'][0][1], "test_img_repeat.jpg")
        self.assertEqual(report['skipped'][0][2], "Already linked")

    def test_multiple_pipe_separated_images(self):
        self._create_media_file('test_img_multi1.jpg')
        self._create_media_file('test_img_multi2.jpg')
        csv_data = """sku,name,category,brand,is_published,is_featured,image_filename
E043309,Ground Rice,Rice,East End,FALSE,FALSE,test_img_multi1.jpg|test_img_multi2.jpg
"""
        dataset = CSV().create_dataset(csv_data)
        result = self.resource.import_data(dataset, dry_run=False)
        self.assertFalse(result.has_errors())

        product = Product.objects.get(sku="E043309")
        self.assertEqual(product.images.count(), 2)

        img1 = product.images.get(image="products/test_img_multi1.jpg")
        img2 = product.images.get(image="products/test_img_multi2.jpg")
        self.assertTrue(img1.is_primary)
        self.assertFalse(img2.is_primary)

        report = self.resource.get_image_report()
        self.assertEqual(report['total_linked'], 2)

    def test_preserve_existing_primary_image(self):
        self._create_media_file('test_img_existing.jpg')
        self._create_media_file('test_img_new.jpg')

        # Create product with an existing primary image
        product = Product.objects.create(
            sku="E043309",
            name="Ground Rice",
            category=self.category_rice,
            brand=self.brand_east_end
        )
        existing_img = ProductImage(
            product=product,
            image="products/test_img_existing.jpg",
            is_primary=True
        )
        super(ProductImage, existing_img).save()

        csv_data = """sku,name,category,brand,is_published,is_featured,image_filename
E043309,Ground Rice,Rice,East End,FALSE,FALSE,test_img_new.jpg
"""
        dataset = CSV().create_dataset(csv_data)
        result = self.resource.import_data(dataset, dry_run=False)
        self.assertFalse(result.has_errors())

        self.assertEqual(product.images.count(), 2)
        existing_img = product.images.get(image="products/test_img_existing.jpg")
        new_img = product.images.get(image="products/test_img_new.jpg")

        # Existing primary must be preserved
        self.assertTrue(existing_img.is_primary)
        self.assertFalse(new_img.is_primary)

    def test_path_traversal_rejection(self):
        csv_data = """sku,name,category,brand,is_published,is_featured,image_filename
E043309,Ground Rice,Rice,East End,FALSE,FALSE,../../etc/passwd|../secret.jpg|sub/test.jpg
"""
        dataset = CSV().create_dataset(csv_data)
        result = self.resource.import_data(dataset, dry_run=False)
        self.assertFalse(result.has_errors())

        product = Product.objects.get(sku="E043309")
        self.assertEqual(product.images.count(), 0)

        report = self.resource.get_image_report()
        self.assertEqual(report['total_linked'], 0)
        self.assertEqual(report['total_skipped'], 3)


class CollectProductImagesCommandTests(TestCase):
    def setUp(self):
        self.category = Category.objects.create(name="Rice", slug="rice")
        self.brand_fudco = Brand.objects.create(name="Fudco", slug="fudco")
        self.brand_ee = Brand.objects.create(name="East End", slug="east-end")

        # Create test products matching known references
        self.p1 = Product.objects.create(
            sku="F050959",
            name="Pawa Thick Rice Flakes",
            slug="pawa-thick-rice-flakes",
            category=self.category,
            brand=self.brand_fudco,
            is_published=False
        )
        self.p2 = Product.objects.create(
            sku="E043309",
            name="Ground Rice",
            slug="ground-rice",
            category=self.category,
            brand=self.brand_ee,
            is_published=False
        )
        self.p3 = Product.objects.create(
            sku="E189911",
            name="Star Aniseeds",
            slug="star-aniseeds",
            category=self.category,
            brand=self.brand_ee,
            is_published=False
        )

        self.test_output = "test_candidate_report.csv"

    def tearDown(self):
        if os.path.exists(self.test_output):
            os.remove(self.test_output)

    def test_dry_run_generates_report_without_modifying_db_or_files(self):
        from django.core.management import call_command
        import csv

        call_command(
            'collect_product_images',
            skus='F050959,E043309,E189911',
            output=self.test_output
        )

        self.assertTrue(os.path.exists(self.test_output))
        with open(self.test_output, 'r', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))

        self.assertEqual(len(rows), 3)
        row_dict = {r['sku']: r for r in rows}

        # Exact match
        self.assertEqual(row_dict['F050959']['confidence'], 'EXACT')
        self.assertIn('fudcoshop.com', row_dict['F050959']['candidate_image_url'])

        # Uncertain match
        self.assertEqual(row_dict['E043309']['confidence'], 'UNCERTAIN')

        # No match
        self.assertEqual(row_dict['E189911']['confidence'], 'NO_MATCH')
        self.assertEqual(row_dict['E189911']['candidate_image_url'], '')

        # Confirm DB unchanged
        self.assertEqual(ProductImage.objects.count(), 0)
        for p in [self.p1, self.p2, self.p3]:
            p.refresh_from_db()
            self.assertFalse(p.is_published)




