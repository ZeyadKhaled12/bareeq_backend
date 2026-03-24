from .models import Region
from rest_framework import serializers
from .models import Gender, Region


class GenderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gender
        fields = ['id', 'name_ar', 'name_en']


class RegionSerializer(serializers.ModelSerializer):
    # This field is populated by the .annotate() in the view
    is_avail = serializers.BooleanField(read_only=True)

    class Meta:
        model = Region
        fields = ['id', 'name_ar', 'name_en', 'is_avail']
