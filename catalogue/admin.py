from django.contrib import admin
from django.utils.text import slugify
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ImportExportModelAdmin
from .models import Category, Brand, Product, PackSize, ProductImage

class ProductResource(resources.ModelResource):

    class Meta:
        model = Product
        fields = (
            'sku', 'name', 'slug', 'category', 'brand', 'description', 'country_of_origin', 
            'ingredients', 'storage_info', 'packaging_info', 'nutrition_info', 
            'is_published', 'is_featured', 'badge', 'meta_title', 'meta_description'
        )
        import_id_fields = ('sku',)
        skip_unchanged = True
        report_skipped = True

    def before_import_row(self, row, **kwargs):
        # Retrieve or create Category by name
        category_name = row.get('category')
        if category_name:
            category, _ = Category.objects.get_or_create(
                name=category_name.strip(),
                defaults={'slug': slugify(category_name.strip())}
            )
            # We map category field internally to Category ID
            row['category'] = category.id

        # Retrieve or create Brand by name
        brand_name = row.get('brand')
        if brand_name:
            brand, _ = Brand.objects.get_or_create(
                name=brand_name.strip(),
                defaults={'slug': slugify(brand_name.strip())}
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
        # If the row import failed or was skipped, do nothing
        if row_result.import_type in ['skip', 'error', 'invalid']:
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


class PackSizeInline(admin.TabularInline):
    model = PackSize
    extra = 1


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'display_order', 'is_active')
    list_editable = ('display_order', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')


from django.utils.html import mark_safe

@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'logo_preview', 'slug', 'is_featured')
    list_editable = ('is_featured',)
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ('name', 'description')
    readonly_fields = ('logo_display',)

    def logo_preview(self, obj):
        if obj.logo:
            return mark_safe(f'<img src="{obj.logo.url}" style="max-height: 36px; max-width: 80px; object-fit: contain; border-radius: 4px; background: #fff; padding: 2px; border: 1px solid #ddd;" />')
        return mark_safe('<span style="color: #999; font-style: italic;">No logo</span>')
    logo_preview.short_description = "Logo"

    def logo_display(self, obj):
        if obj.logo:
            return mark_safe(f'<img src="{obj.logo.url}" style="max-height: 100px; max-width: 220px; object-fit: contain; border-radius: 6px; padding: 6px; border: 1px solid #ccc; background: #fff;" />')
        return "No logo uploaded yet."
    logo_display.short_description = "Current Logo"


@admin.register(Product)
class ProductAdmin(ImportExportModelAdmin):
    resource_class = ProductResource
    list_display = ('name', 'sku', 'category', 'brand', 'is_published', 'is_featured', 'badge')
    list_filter = ('is_published', 'is_featured', 'category', 'brand')
    list_editable = ('is_published', 'is_featured', 'badge')
    search_fields = ('name', 'sku', 'category__name', 'brand__name')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [PackSizeInline, ProductImageInline]
    actions = ['make_published', 'make_unpublished']

    def make_published(self, request, queryset):
        queryset.update(is_published=True)
    make_published.short_description = "Publish selected products"

    def make_unpublished(self, request, queryset):
        queryset.update(is_published=False)
    make_unpublished.short_description = "Unpublish selected products"
