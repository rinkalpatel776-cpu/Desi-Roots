from django.db import models

class FAQ(models.Model):
    question = models.CharField(max_length=255)
    answer = models.TextField()
    display_order = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
        ordering = ['display_order', 'id']

    def __str__(self):
        return self.question


class Testimonial(models.Model):
    quote = models.TextField()
    author = models.CharField(max_length=150)
    business = models.CharField(max_length=150, help_text="e.g., The Curry House, Bristol")
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ['id']

    def __str__(self):
        return f"Testimonial from {self.author} ({self.business})"
