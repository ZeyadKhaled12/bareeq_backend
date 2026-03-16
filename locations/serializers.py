from rest_framework import serializers
from .models import Location
from lists.models import Region


class LocationSerializer(serializers.ModelSerializer):
    # This allows the frontend to send an integer ID
    region_id = serializers.PrimaryKeyRelatedField(
        queryset=Region.objects.all(),
        source='region',
        help_text="The ID of the region from the Cairo regions list."
    )

    class Meta:
        model = Location
        # Notice we EXCLUDE 'user' here because it is handled by the token
        fields = ['id', 'name', 'region_id', 'latitude', 'longitude']
        extra_kwargs = {
            'latitude': {'required': False},
            'longitude': {'required': False},
        }
