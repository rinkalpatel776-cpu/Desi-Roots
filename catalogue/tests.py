
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






class BrandLogoTrimTests(TestCase):
    """Logos are trimmed of empty space so they display at a consistent size."""

    def setUp(self):
        import tempfile
        from django.test import override_settings
        self.media_dir = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media_dir)
        self.override.enable()

    def tearDown(self):
        import shutil
        self.override.disable()
        shutil.rmtree(self.media_dir, ignore_errors=True)

    def make_upload(self, name, mode, size, box, fill, fmt):
        from io import BytesIO
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        background = (0, 0, 0, 0) if mode == 'RGBA' else (255, 255, 255)
        img = Image.new(mode, size, background)
        img.paste(Image.new(mode, (box[2] - box[0], box[3] - box[1]), fill), box[:2])
        buf = BytesIO()
        img.save(buf, format=fmt)
        return SimpleUploadedFile(name, buf.getvalue(), content_type=f'image/{fmt.lower()}')

    def test_transparent_padding_is_trimmed_on_upload(self):
        logo = self.make_upload('pad.png', 'RGBA', (400, 400), (100, 150, 300, 250), (200, 0, 0, 255), 'PNG')
        brand = Brand.objects.create(name='Pad', slug='pad', logo=logo)
        self.assertEqual((brand.logo.width, brand.logo.height), (200, 100))

    def test_white_background_jpeg_is_trimmed_and_saved_as_png(self):
        logo = self.make_upload('white.jpg', 'RGB', (300, 300), (50, 100, 250, 200), (0, 0, 200), 'JPEG')
        brand = Brand.objects.create(name='White', slug='white', logo=logo)
        self.assertTrue(brand.logo.name.endswith('.png'))
        self.assertLessEqual(abs(brand.logo.width - 200), 2)
        self.assertLessEqual(abs(brand.logo.height - 100), 2)

    def test_command_trims_existing_logo_to_new_file_and_is_repeatable(self):
        from io import StringIO
        from django.core.files.base import ContentFile
        from django.core.management import call_command
        brand = Brand.objects.create(name='Old', slug='old')
        upload = self.make_upload('old.png', 'RGBA', (500, 500), (0, 200, 500, 300), (0, 120, 0, 255), 'PNG')
        # Store the padded file directly, as logos uploaded before trimming existed
        name = brand.logo.storage.save('brands/old.png', ContentFile(upload.read()))
        Brand.objects.filter(pk=brand.pk).update(logo=name)

        call_command('trim_brand_logos', stdout=StringIO())
        brand.refresh_from_db()
        self.assertEqual(brand.logo.name, 'brands/old_trim.png')
        self.assertEqual((brand.logo.width, brand.logo.height), (500, 100))
        self.assertFalse(brand.logo.storage.exists('brands/old.png'))

        out = StringIO()
        call_command('trim_brand_logos', stdout=out)
        self.assertIn('Trimmed 0; skipped 1.', out.getvalue())


class ImportCatalogueCsvTests(TestCase):
    """The supplier catalogue importer: grouped products, per-size codes, photos, drafts, re-runs."""

    def setUp(self):
        import tempfile
        from django.test import override_settings
        from PIL import Image
        self.tmp = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=os.path.join(self.tmp, 'media'))
        self.override.enable()
        self.photos = os.path.join(self.tmp, 'photos')
        os.makedirs(self.photos)
        Image.new('RGB', (400, 300), (200, 120, 40)).save(os.path.join(self.photos, 'heera-22022.jpg'))
        self.csv_path = os.path.join(self.tmp, 'products.csv')
        with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['sku', 'name', 'brand', 'category', 'pack_sizes', 'pack_size_skus', 'image_filename'])
            w.writerow(['22022', 'Heera Amchoor Powder', 'Heera', 'Spices & Masalas', '20 x 100 g|10 x 400 g', '22022|22142', 'heera-22022.jpg'])
            w.writerow(['', 'MDH Chana Masala', 'MDH', 'Spices & Masalas', '60 x 100 g|24 x 500 g', '', ''])
            w.writerow(['', 'MDH Kitchen King', 'MDH', 'Spices & Masalas', '60 x 100 g', '', ''])

    def tearDown(self):
        import shutil
        self.override.disable()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_import(self, *extra):
        from io import StringIO
        from django.core.management import call_command
        out = StringIO()
        call_command('import_catalogue_csv', self.csv_path, '--photos', self.photos, *extra, stdout=out)
        return out.getvalue()

    def test_imports_drafts_with_sizes_codes_and_photo(self):
        self.run_import()
        self.assertEqual(Product.objects.count(), 3)
        self.assertFalse(Product.objects.filter(is_published=True).exists())
        heera = Product.objects.get(sku='22022')
        self.assertEqual(heera.brand.name, 'Heera')
        self.assertEqual(heera.category.name, 'Spices & Masalas')
        self.assertEqual([(p.size, p.sku) for p in heera.pack_sizes.all()],
                         [('20 x 100 g', '22022'), ('10 x 400 g', '22142')])
        self.assertEqual(heera.images.count(), 1)
        self.assertTrue(heera.images.first().is_primary)

    def test_products_without_sku_are_stored_as_null(self):
        self.run_import()
        self.assertEqual(Product.objects.filter(sku__isnull=True).count(), 2)
        self.assertEqual(Product.objects.get(name='MDH Chana Masala').pack_sizes.count(), 2)

    def test_rerun_updates_without_duplicates(self):
        self.run_import()
        Product.objects.filter(sku='22022').update(is_published=True)
        out = self.run_import()
        self.assertIn('created: 0, updated: 3', out)
        self.assertEqual(Product.objects.count(), 3)
        self.assertEqual(PackSize.objects.count(), 5)
        self.assertEqual(ProductImage.objects.count(), 1)
        self.assertTrue(Product.objects.get(sku='22022').is_published, 'a re-run must not unpublish')

    def test_dry_run_saves_nothing(self):
        out = self.run_import('--dry-run')
        self.assertIn('Dry run', out)
        self.assertEqual(Product.objects.count(), 0)
        products_dir = os.path.join(self.tmp, 'media', 'products')
        self.assertFalse(os.path.exists(products_dir) and os.listdir(products_dir), 'dry run must not write photos')


class ProductPageSkuDisplayTests(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name='Spices & Masalas', slug='spices-masalas')

    def test_product_without_sku_shows_no_sku_or_none(self):
        p = Product.objects.create(name='MDH Kitchen King', slug='mdh-kitchen-king', category=self.cat, is_published=True)
        PackSize.objects.create(product=p, size='60 x 100 g')
        response = self.client.get(f'/products/{p.slug}/')
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, 'SKU:')
        self.assertNotContains(response, 'None')
        self.assertNotContains(response, '"sku"')

    def test_per_size_codes_are_listed(self):
        p = Product.objects.create(name='East End Sunflower Oil', slug='east-end-sunflower-oil', sku='E048935',
                                   category=self.cat, is_published=True)
        PackSize.objects.create(product=p, size='3 x 5 ltr', sku='E048935', display_order=0)
        PackSize.objects.create(product=p, size='6 x 2 ltr', sku='E000815', display_order=1)
        response = self.client.get(f'/products/{p.slug}/')
        self.assertContains(response, '6 x 2 ltr: E000815')
        self.assertContains(response, 'SKU: <span class="font-monospace text-dark">E048935</span>', html=False)


class PublishRequiresPhotoTests(TestCase):
    """A product can only be published once it has a photo."""

    def setUp(self):
        import tempfile
        from django.contrib.auth.models import User
        from django.test import override_settings
        self.tmp = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.tmp)
        self.override.enable()
        self.client.force_login(User.objects.create_superuser('staff', 'staff@example.test', 'test-pass-123'))
        self.cat = Category.objects.create(name='Spices & Masalas', slug='spices-masalas')
        self.no_photo = Product.objects.create(name='No Photo', slug='no-photo', sku='NP1', category=self.cat, is_published=False)
        self.with_photo = Product.objects.create(name='With Photo', slug='with-photo', sku='WP1', category=self.cat, is_published=False)
        self.add_photo(self.with_photo)

    def tearDown(self):
        import shutil
        self.override.disable()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def add_photo(self, product):
        from io import BytesIO
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        buf = BytesIO()
        Image.new('RGB', (200, 150), (180, 90, 30)).save(buf, format='JPEG')
        ProductImage.objects.create(product=product, is_primary=True,
                                    image=SimpleUploadedFile('p.jpg', buf.getvalue(), content_type='image/jpeg'))

    def change_url(self, product):
        from django.urls import reverse
        return reverse('admin:catalogue_product_change', args=[product.pk])

    def edit_payload(self, product):
        return {
            'name': product.name, 'slug': product.slug, 'sku': product.sku, 'category': self.cat.pk,
            'is_published': 'on',
            'pack_sizes-TOTAL_FORMS': '0', 'pack_sizes-INITIAL_FORMS': '0',
            'images-TOTAL_FORMS': '0', 'images-INITIAL_FORMS': str(product.images.count()),
            **{f'images-{i}-id': img.pk for i, img in enumerate(product.images.all())},
            **{f'images-{i}-product': product.pk for i, _ in enumerate(product.images.all())},
        }

    def test_model_rule_unpublishes_product_without_photo(self):
        self.no_photo.is_published = True
        self.no_photo.save()
        self.assertTrue(self.no_photo.unpublish_if_no_photo())
        self.assertFalse(Product.objects.get(pk=self.no_photo.pk).is_published)
        self.with_photo.is_published = True
        self.with_photo.save()
        self.assertFalse(self.with_photo.unpublish_if_no_photo())

    def test_bulk_publish_skips_products_without_photo(self):
        from django.urls import reverse
        response = self.client.post(reverse('admin:catalogue_product_changelist'), {
            'action': 'make_published', '_selected_action': [self.no_photo.pk, self.with_photo.pk]}, follow=True)
        self.assertTrue(Product.objects.get(pk=self.with_photo.pk).is_published)
        self.assertFalse(Product.objects.get(pk=self.no_photo.pk).is_published)
        self.assertContains(response, 'left as drafts because they have no photo yet')

    def test_edit_page_keeps_product_without_photo_as_draft(self):
        payload = self.edit_payload(self.no_photo)
        payload['images-INITIAL_FORMS'] = '0'
        response = self.client.post(self.change_url(self.no_photo), payload, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Product.objects.get(pk=self.no_photo.pk).is_published)
        self.assertContains(response, 'can only be published once it has a photo')

    def test_edit_page_publishes_product_with_photo(self):
        response = self.client.post(self.change_url(self.with_photo), self.edit_payload(self.with_photo), follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(Product.objects.get(pk=self.with_photo.pk).is_published)


class ProductCardEnquireTests(TestCase):
    def test_card_has_enquire_button_and_links_to_product(self):
        cat = Category.objects.create(name='Spices & Masalas', slug='spices-masalas')
        p = Product.objects.create(name='Allinson Yeast', slug='allinson-yeast', category=cat, is_published=True, badge='Trending')
        response = self.client.get('/products/')
        self.assertContains(response, f'href="/contact/?product_id={p.id}"')
        self.assertContains(response, 'Enquire')
        self.assertNotContains(response, 'View Details')
        self.assertContains(response, 'href="/products/allinson-yeast/" class="sp-card-title-link"')
        self.assertContains(response, 'class="sp-badge sp-card-badge"')


class CatalogueSidebarCountTests(TestCase):
    def test_counts_only_published_products_and_hides_empty_categories(self):
        rice = Category.objects.create(name='Rice', slug='rice')
        Category.objects.create(name='Empty', slug='empty')
        Product.objects.create(name='Live Rice', slug='live-rice', category=rice, is_published=True)
        Product.objects.create(name='Draft Rice', slug='draft-rice', category=rice, is_published=False)
        response = self.client.get('/products/')
        cats = {c.name: c.published_count for c in response.context['categories']}
        self.assertEqual(cats, {'Rice': 1})


class BrandDeleteCascadeTests(TestCase):
    """Deleting a brand deletes its products, their pack sizes and photos (files too); enquiries are kept."""

    def setUp(self):
        import tempfile
        from django.test import override_settings
        self.tmp = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.tmp)
        self.override.enable()
        self.cat = Category.objects.create(name='Spices & Masalas', slug='spices-masalas')
        self.tata = Brand.objects.create(name='Tata', slug='tata')
        self.other = Brand.objects.create(name='Heera', slug='heera')
        self.salt = Product.objects.create(name='Tata Salt', slug='tata-salt', category=self.cat, brand=self.tata)
        self.keep = Product.objects.create(name='Heera Salt', slug='heera-salt', category=self.cat, brand=self.other)
        PackSize.objects.create(product=self.salt, size='30 x 1 kg', sku='05590')
        from io import BytesIO
        from PIL import Image
        from django.core.files.uploadedfile import SimpleUploadedFile
        buf = BytesIO()
        Image.new('RGB', (200, 150), (200, 200, 200)).save(buf, format='JPEG')
        self.img = ProductImage.objects.create(product=self.salt, is_primary=True,
                                               image=SimpleUploadedFile('salt.jpg', buf.getvalue(), content_type='image/jpeg'))

    def tearDown(self):
        import shutil
        self.override.disable()
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_deleting_brand_deletes_its_products_and_photo_files(self):
        from enquiries.models import Enquiry
        enquiry = Enquiry.objects.create(name='A', email='a@example.test', phone='1', message='Salt please', product=self.salt)
        image_path, thumb_path = self.img.image.path, self.img.thumbnail.path
        self.assertTrue(os.path.exists(image_path))
        self.tata.delete()
        self.assertFalse(Product.objects.filter(pk=self.salt.pk).exists())
        self.assertFalse(PackSize.objects.filter(sku='05590').exists())
        self.assertFalse(ProductImage.objects.exists())
        self.assertFalse(os.path.exists(image_path))
        self.assertFalse(os.path.exists(thumb_path))
        self.assertTrue(Product.objects.filter(pk=self.keep.pk).exists(), "other brands' products stay")
        enquiry.refresh_from_db()
        self.assertIsNone(enquiry.product, 'the enquiry is kept, with the product link cleared')

    def test_shared_photo_file_is_kept_while_another_product_uses_it(self):
        shared = ProductImage(product=self.keep, image=self.img.image.name, thumbnail=self.img.thumbnail.name)
        super(ProductImage, shared).save()  # link the same file, as the admin CSV import can
        self.tata.delete()
        self.assertTrue(os.path.exists(shared.image.path))


class FooterAndMobileFilterTests(TestCase):
    def setUp(self):
        from django.core.cache import cache
        cache.clear()
        self.rice = Category.objects.create(name='Rice', slug='rice')
        self.spices = Category.objects.create(name='Spices & Masalas', slug='spices-masalas')
        Category.objects.create(name='Pickles', slug='pickles')  # no products
        self.heera = Brand.objects.create(name='Heera', slug='heera')
        self.unused = Brand.objects.create(name='East End', slug='east-end')
        for i in range(3):
            Product.objects.create(name=f'Spice {i}', slug=f'spice-{i}', category=self.spices, brand=self.heera, is_published=True)
        Product.objects.create(name='Rice 1', slug='rice-1', category=self.rice, brand=self.heera, is_published=True)
        Product.objects.create(name='Draft', slug='draft', category=self.rice, brand=self.unused, is_published=False)

    def test_footer_links_to_categories_with_published_products(self):
        response = self.client.get('/')
        self.assertEqual([c['slug'] for c in response.context['footer_categories']], ['spices-masalas', 'rice'])
        self.assertContains(response, 'href="/products/?category=spices-masalas"')
        self.assertNotContains(response, 'href="/products/?category=pickles"')

    def test_phone_filter_toggle_and_only_brands_with_products(self):
        response = self.client.get('/products/')
        self.assertContains(response, 'data-bs-target="#catalogueFilters"')
        self.assertContains(response, 'class="collapse d-lg-block" id="catalogueFilters"')
        self.assertEqual([b.name for b in response.context['brands']], ['Heera'])
