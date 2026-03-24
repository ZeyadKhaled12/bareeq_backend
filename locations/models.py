from django.db import models
from django.conf import settings
from lists.models import Region


class Location(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='locations',
        null=True, blank=True  # Allow null for existing data
    )
    region = models.ForeignKey(
        Region,
        on_delete=models.PROTECT,
        related_name='locations'
    )

    name = models.CharField(max_length=255)  # e.g., "Home", "Work"
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        # Accessing phone via the related profile
        # This assumes your UserProfile has a OneToOneField to User with related_name='profile'
        user_phone = "No Phone"
        if hasattr(self.user, 'profile'):
            user_phone = self.user.profile.phone

        return f"{self.name} ({user_phone})"
