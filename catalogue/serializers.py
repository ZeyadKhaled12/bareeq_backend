from rest_framework import serializers
from .models import Service


class ServiceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'name_en', 'name_ar']
