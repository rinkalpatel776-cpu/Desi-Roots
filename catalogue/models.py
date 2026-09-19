from django.db import models
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
import os

class Category(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, db_index=True)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name


class Brand(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, db_index=True)
    logo = models.ImageField(upload_to='brands/', blank=True, null=True)
    description = models.TextField(blank=True)
    is_featured = models.BooleanField(default=False, db_index=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=240, unique=True, db_index=True)
    sku = models.CharField(max_length=100, unique=True, db_index=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name='products')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, blank=True, null=True, related_name='products')
    description = models.TextField(blank=True)
    country_of_origin = models.CharField(max_length=100, blank=True)
    ingredients = models.TextField(blank=True)
    storage_info = models.TextField(blank=True)
    packaging_info = models.TextField(blank=True)
    nutrition_info = models.TextField(blank=True)
    is_published = models.BooleanField(default=True, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    badge = models.CharField(max_length=50, blank=True, help_text="e.g., Best Seller, New, Featured")
    meta_title = models.CharField(max_length=150, blank=True)
    meta_description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.sku})"


class PackSize(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='pack_sizes')
    size = models.CharField(max_length=50, help_text="e.g., 5kg, 400g, 10kg")
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['display_order', 'id']

    def __str__(self):
        return f"{self.product.name} - {self.size}"


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='products/')
    thumbnail = models.ImageField(upload_to='products/thumbnails/', blank=True, null=True)
    alt_text = models.CharField(max_length=200, blank=True)
    is_primary = models.BooleanField(default=False)

    class Meta:
        ordering = ['-is_primary', 'id']

    def save(self, *args, **kwargs):
        if self.image:
            try:
                # check if file is newly uploaded
                is_new = hasattr(self.image, 'file') or not self.pk
            except Exception:
                is_new = True

            if is_new:
                img = Image.open(self.image)
                original_format = img.format or 'JPEG'
                original_filename, original_ext = os.path.splitext(self.image.name)
                
                if img.mode in ('RGBA', 'LA') and original_format == 'JPEG':
                    background = Image.new('RGB', img.size, (255, 255, 255))
                    background.paste(img, mask=img.split()[3])
                    img = background

                # Primary optimized image
                img.thumbnail((800, 600))
                output = BytesIO()
                img.save(output, format=original_format, quality=85)
                output.seek(0)
                
                self.image = InMemoryUploadedFile(
                    output, 
                    'ImageField', 
                    f"{original_filename}{original_ext}", 
                    f"image/{original_format.lower()}", 
                    sys.getsizeof(output), 
                    None
                )

                # Thumbnail image
                thumb = img.copy()
                thumb.thumbnail((300, 225))
                thumb_output = BytesIO()
                thumb.save(thumb_output, format=original_format, quality=80)
                thumb_output.seek(0)
                
                self.thumbnail = InMemoryUploadedFile(
                    thumb_output, 
                    'ImageField', 
                    f"{original_filename}_thumb{original_ext}", 
                    f"image/{original_format.lower()}", 
                    sys.getsizeof(thumb_output), 
                    None
                )

        super().save(*args, **kwargs)

    def __str__(self):
        return f"Image for {self.product.name} (Primary: {self.is_primary})"
