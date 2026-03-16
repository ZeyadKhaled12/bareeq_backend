from rest_framework import serializers
from .models import Gender, Region


class GenderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gender
        fields = ['id', 'name_ar', 'name_en']


class RegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ['id', 'name_en', 'name_ar']
