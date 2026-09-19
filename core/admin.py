from django.contrib import admin
from .models import SiteSettings

@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    list_display = ('__str__', 'phone_number', 'email_address')
    
    def has_add_permission(self, request):
        # Allow adding settings only if none exist
        return not SiteSettings.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Do not allow deleting settings
        return False
