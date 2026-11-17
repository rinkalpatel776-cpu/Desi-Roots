from django.db import models
from django.core.exceptions import ValidationError

class SiteSettings(models.Model):
    announcement_bar = models.CharField(
        max_length=255, 
        blank=True, 
        help_text="Text shown in the announcement bar at the top of every page."
    )
    phone_number = models.CharField(
        max_length=50, 
        blank=True, 
        help_text="Main contact phone number."
    )
    whatsapp_link = models.URLField(
        blank=True, 
        help_text="Full link for the WhatsApp contact (e.g., https://wa.me/447...)."
    )
    email_address = models.EmailField(
        blank=True, 
        help_text="Main support / business contact email."
    )
    postal_address = models.TextField(
        blank=True, 
        help_text="Full postal address of the business. Required for legal pages."
    )
    vat_number = models.CharField(
        "VAT number", max_length=30, blank=True,
        help_text="Shown in the footer and on the Contact page, e.g. GB 515 3463 07. Leave blank to hide it.",
    )
    facebook_url = models.URLField(blank=True, help_text="Link to Facebook profile.")
    instagram_url = models.URLField(blank=True, help_text="Link to Instagram profile.")
    linkedin_url = models.URLField(blank=True, help_text="Link to LinkedIn profile.")
    
    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

    def clean(self):
        # Prevent creating multiple instances of SiteSettings
        if not self.pk and SiteSettings.objects.exists():
            raise ValidationError("There can only be one instance of Site Settings.")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return "Desi Roots Site Settings"
