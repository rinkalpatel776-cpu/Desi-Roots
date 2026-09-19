from .models import SiteSettings

def site_settings(request):
    try:
        settings = SiteSettings.objects.first()
    except Exception:
        settings = None

    if not settings:
        # Return an unsaved default instance so properties are accessible but empty
        settings = SiteSettings()

    return {
        'site_settings': settings
    }
