from django.contrib import admin
from .models import FAQ, Testimonial

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'display_order', 'is_active')
    list_editable = ('display_order', 'is_active')
    search_fields = ('question', 'answer')


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('author', 'business', 'is_active')
    list_editable = ('is_active',)
    search_fields = ('author', 'business', 'quote')
