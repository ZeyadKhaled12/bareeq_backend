from django.db import models
from django.conf import settings
from lists.models import Region


class Location(models.Model):
    # 'user' is automatically linked via the Token
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='locations'
    )
    # 'region' is required from your Cairo list
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
        return f"{self.name} - {self.user.phone}"
