from django.contrib import admin
from .models import Enquiry

@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ('business_name', 'name', 'email', 'phone', 'product', 'status', 'created_at')
    list_filter = ('status', 'created_at', 'business_type')
    list_editable = ('status',)
    search_fields = ('name', 'business_name', 'email', 'phone', 'message', 'admin_notes')
    readonly_fields = ('created_at',)
    fieldsets = (
        ('Contact Info', {
            'fields': ('name', 'business_name', 'business_type', 'email', 'phone', 'consent_given')
        }),
        ('Enquiry Details', {
            'fields': ('product', 'category_interest', 'message')
        }),
        ('Admin Actions', {
            'fields': ('status', 'admin_notes', 'created_at')
        }),
    )


