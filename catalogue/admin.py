import os
from django.conf import settings
from django.contrib import admin, messages
from django.db import models
from django.utils.text import slugify
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ImportExportModelAdmin
from .models import Category, Brand, Product, PackSize, ProductImage

class ProductResource(resources.ModelResource):
    image_filename = fields.Field(column_name='image_filename', readonly=True)

    class Meta:
        model = Product
        fields = (
            'sku', 'name', 'slug', 'category', 'brand', 'description', 'country_of_origin', 
            'ingredients', 'storage_info', 'packaging_info', 'nutrition_info', 
            'is_published', 'is_featured', 'badge', 'meta_title', 'meta_description',
            'image_filename'
        )
        import_id_fields = ('sku',)
        skip_unchanged = True
        report_skipped = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.image_report = {
            'linked': [],
            'missing': [],
            'skipped': [],
        }

    def before_import(self, dataset, **kwargs):
        super().before_import(dataset, **kwargs)
        self.image_report = {
            'linked': [],
            'missing': [],
            'skipped': [],
        }

    def dehydrate_image_filename(self, product):
        images = [os.path.basename(img.image.name) for img in product.images.all() if img.image]
        return '|'.join(images)

    def get_image_report(self):
        return {
            'linked': list(self.image_report['linked']),
            'missing': list(self.image_report['missing']),
            'skipped': list(self.image_report['skipped']),
            'total_linked': len(self.image_report['linked']),
            'total_missing': len(self.image_report['missing']),
            'total_skipped': len(self.image_report['skipped']),
        }

    def before_import_row(self, row, **kwargs):
        # Retrieve or create Category by case-insensitive name or slug
        category_name = row.get('category')
        if category_name:
            clean_cat_name = str(category_name).strip()
            cat_slug = slugify(clean_cat_name)
            category = Category.objects.filter(
                models.Q(slug=cat_slug) | models.Q(name__iexact=clean_cat_name)
            ).first()
            if not category:
                category = Category.objects.create(
                    name=clean_cat_name,
                    slug=cat_slug
                )
            # We map category field internally to Category ID
            row['category'] = category.id

        # Retrieve or create Brand by case-insensitive name or slug
        brand_name = row.get('brand')
        if brand_name:
            clean_brand_name = str(brand_name).strip()
            brand_slug = slugify(clean_brand_name)
            brand = Brand.objects.filter(
                models.Q(slug=brand_slug) | models.Q(name__iexact=clean_brand_name)
            ).first()
            if not brand:
                brand = Brand.objects.create(
                    name=clean_brand_name,
                    slug=brand_slug
                )
            # Map brand field internally to Brand ID
            row['brand'] = brand.id
        else:
            row['brand'] = None

        # Prepopulate slug if missing
        if not row.get('slug') and row.get('name'):
            base_slug = slugify(row['name'])
            slug = base_slug
            sku = row.get('sku', '')
            if Product.objects.filter(slug=slug).exclude(sku=sku).exists():
                slug = f"{base_slug}-{slugify(sku)}"
            row['slug'] = slug

    def after_import_row(self, row, row_result, **kwargs):
        # If the row import failed or was invalid, do nothing
        if row_result.import_type in ['error', 'invalid']:
            return

        # Find the product instance
        try:
            product = Product.objects.get(sku=row.get('sku'))
        except Product.DoesNotExist:
            return

        # Parse pack sizes pipe-separated values (e.g. 5kg|10kg|20kg)
        pack_sizes_str = row.get('pack_sizes')
        if pack_sizes_str:
            sizes = [s.strip() for s in pack_sizes_str.split('|') if s.strip()]
            
            # Remove any sizes that are no longer present
            product.pack_sizes.exclude(size__in=sizes).delete()
            
            # Create or update sizes
            for idx, size in enumerate(sizes):
                PackSize.objects.get_or_create(
                    product=product,
                    size=size,
                    defaults={'display_order': idx}
                )

        # Parse image filenames if present (pipe-separated e.g. "img1.jpg|img2.jpg")
        image_filenames_str = row.get('image_filename')
        if image_filenames_str:
            raw_entries = [f.strip() for f in str(image_filenames_str).split('|') if f.strip()]
            products_dir = os.path.realpath(os.path.join(settings.MEDIA_ROOT, 'products'))
            has_primary = product.images.filter(is_primary=True).exists()
            dry_run = kwargs.get('dry_run', False)

            for raw_filename in raw_entries:
                # Security: prevent path traversal (reject separators and leading dots)
                if '/' in raw_filename or '\\' in raw_filename or raw_filename.startswith('.'):
                    self.image_report['skipped'].append((
                        product.sku, 
                        raw_filename, 
                        'Path traversal rejected: directory separators or leading dots not allowed'
                    ))
                    continue

                clean_name = os.path.basename(raw_filename)
                if not clean_name:
                    continue

                full_path = os.path.realpath(os.path.join(products_dir, clean_name))

                # Security: ensure file resides strictly inside MEDIA_ROOT/products/
                if os.path.dirname(full_path) != products_dir:
                    self.image_report['skipped'].append((
                        product.sku, 
                        raw_filename, 
                        'Path traversal rejected: resolved path outside products directory'
                    ))
                    continue

                # Existence check: only link if file physically exists on disk
                if not os.path.isfile(full_path):
                    self.image_report['missing'].append((product.sku, clean_name))
                    continue

                rel_path = f"products/{clean_name}"

                # Idempotency: avoid duplicate ProductImage records if already linked
                if product.images.filter(models.Q(image=rel_path) | models.Q(image=clean_name)).exists():
                    self.image_report['skipped'].append((product.sku, clean_name, 'Already linked'))
                    continue

                # Primary image handling: set as primary only if product has no primary image
                is_primary = False
                if not has_primary:
                    is_primary = True
                    has_primary = True

                # Generate thumbnail if not existing
                thumb_name = None
                thumb_dir = os.path.join(products_dir, 'thumbnails')
                base_name, ext = os.path.splitext(clean_name)
                candidate_thumb = f"{base_name}_thumb{ext}"
                thumb_full_path = os.path.join(thumb_dir, candidate_thumb)

                if not dry_run:
                    os.makedirs(thumb_dir, exist_ok=True)
                    if not os.path.exists(thumb_full_path):
                        try:
                            from PIL import Image as PilImage
                            with PilImage.open(full_path) as img:
                                thumb_img = img.copy()
                                thumb_img.thumbnail((300, 225))
                                thumb_img.save(thumb_full_path, quality=80)
                        except Exception:
                            pass

                if os.path.exists(thumb_full_path) or dry_run:
                    thumb_name = f"products/thumbnails/{candidate_thumb}"

                # Create ProductImage instance
                pi = ProductImage(
                    product=product,
                    image=rel_path,
                    thumbnail=thumb_name,
                    alt_text=product.name,
                    is_primary=is_primary
                )
                super(ProductImage, pi).save()
                self.image_report['linked'].append((product.sku, clean_name, is_primary))

        # A row can't publish a product that still has no photo
        product.unpublish_if_no_photo()


class PackSizeInline(admin.TabularInline):
    model = PackSize
    extra = 1


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'display_order', 'is_active', 'show_on_home')
    list_editable = ('display_order', 'is_active', 'show_on_home')
    list_filter = ('show_on_home', 'is_active')

    def changelist_view(self, request, extra_context=None):
        # Tell staff exactly which categories make it onto the home page
        if request.method == 'GET':
            limit = Category.HOME_PAGE_LIMIT
            eligible = Category.for_home_page()
            names = list(eligible.values_list('name', flat=True))
            shown, hidden = names[:limit], names[limit:]
            if not eligible.filter(show_on_home=True).exists():
                messages.info(request, (
                    f"No categories are ticked, so the home page shows the first {limit} by display order: "
                    f"{', '.join(shown)}. Tick \"Show on home page\" to choose them yourself."
                ))
            elif hidden:
                messages.warning(request, (
                    f"The home page shows only {limit} categories. Showing: {', '.join(shown)}. "
                    f"Ticked but not shown: {', '.join(hidden)}. Untick categories or change their "
                    f"Display order to choose which {limit} appear."
                ))
            else:
                messages.info(request, f"Home page shows: {', '.join(shown)}.")
            unpublished = Category.objects.filter(show_on_home=True).exclude(
                pk__in=eligible.values('pk')).values_list('name', flat=True)
            if unpublished:
                messages.warning(request, (
                    f"Ticked but hidden because they are inactive or have no published products: "
                    f"{', '.join(unpublished)}."
                ))
        return super().changelist_view(request, extra_context)
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')


from django.utils.html import format_html, mark_safe

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'logo_preview', 'slug', 'is_featured', 'home_order')
    list_editable = ('is_featured', 'home_order')
    list_filter = ('is_featured',)

    def changelist_view(self, request, extra_context=None):
        # Tell staff exactly which ticked brands make it onto the home page
        if request.method == 'GET':
            ticked = list(Brand.ticked_for_home_page().values_list('name', flat=True))
            shown, hidden = ticked[:Brand.HOME_PAGE_LIMIT], ticked[Brand.HOME_PAGE_LIMIT:]
            if hidden:
                messages.warning(request, (
                    f"The home page shows only {Brand.HOME_PAGE_LIMIT} brands. Showing: {', '.join(shown)}. "
                    f"Ticked but not shown: {', '.join(hidden)}. Untick brands or change their "
                    f"Home page order to choose which {Brand.HOME_PAGE_LIMIT} appear."
                ))
            elif shown:
                messages.info(request, f"Home page shows: {', '.join(shown)}.")
            else:
                messages.info(request, "No brands are ticked, so the Shop by Brand slider is hidden on the home page.")
        return super().changelist_view(request, extra_context)
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')
    readonly_fields = ('logo_display',)

    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="max-height: 36px; max-width: 80px; object-fit: contain; border-radius: 4px; background: #fff; padding: 2px; border: 1px solid #ddd;" />', obj.logo.url)
        return mark_safe('<span style="color: #999; font-style: italic;">No logo</span>')
    logo_preview.short_description = "Logo"

    def logo_display(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="max-height: 100px; max-width: 220px; object-fit: contain; border-radius: 6px; padding: 6px; border: 1px solid #ccc; background: #fff;" />', obj.logo.url)
        return "No logo uploaded yet."
    logo_display.short_description = "Current Logo"


class HasPhotoFilter(admin.SimpleListFilter):
    title = 'photo'
    parameter_name = 'has_photo'

    def lookups(self, request, model_admin):
        return [('yes', 'Has a photo'), ('no', 'No photo yet')]

    def queryset(self, request, queryset):
        if self.value() == 'yes':
            return queryset.filter(photo_count__gt=0)
        if self.value() == 'no':
            return queryset.filter(photo_count=0)
        return queryset


NO_PHOTO_MESSAGE = "A product can only be published once it has a photo."


@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductResource
    list_display = ('name', 'sku', 'category', 'brand', 'has_photo_column', 'is_published', 'is_featured', 'badge')
    list_select_related = ('category', 'brand')  # brand is optional, so Django won't join it on its own
    list_filter = ('is_published', HasPhotoFilter, 'is_featured', 'category', 'brand')
    list_editable = ('is_published', 'is_featured', 'badge')
    search_fields = ('name', 'sku', 'category__name', 'brand__name')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [PackSizeInline, ProductImageInline]
    actions = ['make_published', 'make_unpublished']

    def get_queryset(self, request):
        # One query for the photo column and filter, not one per row
        return super().get_queryset(request).annotate(photo_count=models.Count('images'))

    @admin.display(boolean=True, description='Photo', ordering='photo_count')
    def has_photo_column(self, obj):
        return obj.photo_count > 0

    def save_related(self, request, form, formsets, change):
        # Runs after inline photos are saved, for both the edit page and the list's checkboxes
        super().save_related(request, form, formsets, change)
        if form.instance.unpublish_if_no_photo():
            messages.warning(request, f"\"{form.instance.name}\" was saved as a draft. {NO_PHOTO_MESSAGE}")

    def make_published(self, request, queryset):
        ids = list(queryset.filter(photo_count__gt=0).values_list('pk', flat=True))
        published = Product.objects.filter(pk__in=ids).update(is_published=True)
        skipped = queryset.count() - len(ids)
        messages.success(request, f"Published {published} product(s).")
        if skipped:
            messages.warning(request, f"{skipped} product(s) were left as drafts because they have no photo yet.")
    make_published.short_description = "Publish selected products"

    def make_unpublished(self, request, queryset):
        queryset.update(is_published=False)
    make_unpublished.short_description = "Unpublish selected products"
