# ══════════════════════════════════════════════════════════════════════════
# apps/locations/models.py
# ══════════════════════════════════════════════════════════════════════════
from django.db import models
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _

User = get_user_model()


class Location(models.Model):
    """
    A geographic point a user cares about.
    user=None → anonymous / system-wide location used for public data.
    """
    user       = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='locations',
        null=True, blank=True
    )
    name       = models.CharField(max_length=200, help_text='Display name')
    city       = models.CharField(max_length=100)
    country    = models.CharField(max_length=100)
    country_code = models.CharField(max_length=5, blank=True)
    state      = models.CharField(max_length=100, blank=True)
    latitude   = models.DecimalField(max_digits=9, decimal_places=6)
    longitude  = models.DecimalField(max_digits=9, decimal_places=6)
    timezone   = models.CharField(max_length=60, default='UTC')
    is_default = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('user', 'latitude', 'longitude')
        indexes = [
            models.Index(fields=['latitude', 'longitude']),
            models.Index(fields=['user', 'is_default']),
        ]

    def save(self, *args, **kwargs):
        # Ensure only one default per user
        if self.is_default and self.user:
            Location.objects.filter(user=self.user, is_default=True).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.city}, {self.country}'