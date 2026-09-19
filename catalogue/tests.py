from django.test import TestCase, Client
from django.utils.text import slugify
from .models import Category, Brand, Product, PackSize

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

