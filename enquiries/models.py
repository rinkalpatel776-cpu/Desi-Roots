from django.db import models
from catalogue.models import Product

class Enquiry(models.Model):
    # Asked on the contact form since 24 Nov 2026 (optional), the same audience the site names everywhere
    BUSINESS_TYPE_CHOICES = [
        ('restaurant', 'Restaurant'),
        ('takeaway', 'Takeaway'),
        ('catering', 'Catering company'),
        ('shop', 'Shop or retailer'),
        ('other', 'Other food business'),
    ]
    STATUS_CHOICES = [
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('closed', 'Closed'),
    ]

    name = models.CharField(max_length=150)
    business_name = models.CharField(max_length=150, blank=True, default='')
    business_type = models.CharField(max_length=100, blank=True, default='', choices=BUSINESS_TYPE_CHOICES)
    email = models.EmailField()
    phone = models.CharField(max_length=50)
    postcode = models.CharField('delivery postcode', max_length=8, blank=True, default='')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, blank=True, null=True, related_name='enquiries')
    category_interest = models.CharField(max_length=100, blank=True, default='')
    message = models.TextField()
    consent_given = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new', db_index=True)
    admin_notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Enquiries"
        ordering = ['-created_at']

    @property
    def reference(self):
        """Short reference shown in emails, e.g. DR-123, so replies can be matched to this enquiry."""
        return f"DR-{self.pk}" if self.pk else ""

    def __str__(self):
        if self.business_name:
            return f"Enquiry from {self.business_name} ({self.name})"
        return f"Enquiry from {self.name}"
