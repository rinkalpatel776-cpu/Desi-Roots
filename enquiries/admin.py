import re

from django.contrib import admin
from .models import Enquiry

@admin.register(Enquiry)
class EnquiryAdmin(admin.ModelAdmin):
    list_display = ('reference', 'business_name', 'business_type', 'postcode', 'name', 'email', 'phone', 'status', 'created_at')
    list_filter = ('status', 'business_type', 'created_at')
    list_editable = ('status',)
    search_fields = ('name', 'business_name', 'email', 'phone', 'postcode', 'message', 'admin_notes')
    readonly_fields = ('reference', 'created_at')
    fieldsets = (
        # Product and category interest are not asked for on the contact form, so they are
        # left out here (the database columns are kept). Business type and postcode: since 24 Nov 2026.
        ('Contact Info', {
            'fields': ('name', 'business_name', 'business_type', 'email', 'phone', 'postcode', 'consent_given')
        }),
        ("Customer's Message", {
            'fields': ('message',)
        }),
        ('Admin Actions', {
            'fields': ('reference', 'status', 'admin_notes', 'created_at')
        }),
    )

    def get_search_results(self, request, queryset, search_term):
        # Typing a reference such as "DR-123" (from an email subject) finds that enquiry
        match = re.fullmatch(r'\s*DR-?(\d+)\s*', search_term, re.IGNORECASE)
        if match:
            return queryset.filter(pk=int(match.group(1))), False
        return super().get_search_results(request, queryset, search_term)
