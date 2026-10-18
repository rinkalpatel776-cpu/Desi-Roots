from django.db import models
from PIL import Image, ImageChops
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys
import os


def trim_logo_border(img):
    """
    Crop the empty space around a logo so every logo fills its box the same way.
    Uses transparency when the image has any, otherwise treats near-white as empty.
    Returns (image, changed).
    """
    rgba = img.convert('RGBA')
    alpha = rgba.getchannel('A')
    if alpha.getextrema()[0] < 255:
        mask = alpha.point(lambda v: 255 if v > 16 else 0)
    else:
        white = Image.new('RGB', rgba.size, (255, 255, 255))
        mask = ImageChops.difference(rgba.convert('RGB'), white).convert('L').point(lambda v: 255 if v > 18 else 0)
    bbox = mask.getbbox()
    if not bbox or bbox == (0, 0, rgba.width, rgba.height):
        return img, False
    return rgba.crop(bbox), True


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
    # How many brands the home page Featured Brands section shows (one row of 4)
    HOME_PAGE_LIMIT = 4

    name = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True, db_index=True)
    logo = models.ImageField(upload_to='brands/', blank=True, null=True)
    description = models.TextField(blank=True)
    is_featured = models.BooleanField(
        "Show on home page", default=False, db_index=True,
        help_text="Tick to show this brand in the Featured Brands section of the home page.",
    )
    home_order = models.PositiveIntegerField(
        "Home page order", default=0,
        help_text="Lower numbers appear first on the home page. Brands with the same number are sorted by name.",
    )

    class Meta:
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Trim empty space from newly uploaded logos; saved as PNG to keep transparency
        if self.logo and not self.logo._committed:
            img, changed = trim_logo_border(Image.open(self.logo))
            if changed:
                output = BytesIO()
                img.save(output, format='PNG', optimize=True)
                output.seek(0)
                base_name = os.path.splitext(os.path.basename(self.logo.name))[0]
                self.logo = InMemoryUploadedFile(
                    output, 'ImageField', f"{base_name}.png", 'image/png', output.getbuffer().nbytes, None
                )
        super().save(*args, **kwargs)

    @classmethod
    def ticked_for_home_page(cls):
        """Every brand ticked 'Show on home page', in home page order."""
        return cls.objects.filter(is_featured=True).order_by('home_order', 'name')


class Product(models.Model):
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=240, unique=True, db_index=True)
    # Optional: some supplier lists have no codes. NULL (not '') so uniqueness still holds for real SKUs.
    sku = models.CharField(max_length=100, unique=True, db_index=True, blank=True, null=True)
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
        return f"{self.name} ({self.sku})" if self.sku else self.name

    def save(self, *args, **kwargs):
        # Store a missing SKU as NULL so several products can have none
        if not self.sku:
            self.sku = None
        super().save(*args, **kwargs)

    def has_photo(self):
        return self.images.exists()

    def unpublish_if_no_photo(self):
        """A product may only be published once it has a photo. Returns True if it was unpublished."""
        if self.is_published and not self.has_photo():
            self.is_published = False
            self.save(update_fields=['is_published'])
            return True
        return False


class PackSize(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='pack_sizes')
    size = models.CharField(max_length=50, help_text="e.g., 5kg, 400g, 10kg")
    sku = models.CharField(max_length=100, blank=True, db_index=True, help_text="Supplier code for this size, if any.")
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
