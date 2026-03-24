from rest_framework import serializers
from .models import Service, Category, Item, ItemServicePrice


class ServiceListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Service
        fields = ['id', 'name_en', 'name_ar']


class CategoryListSerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name_en', 'name_ar']


class ItemServicePriceSerializer(serializers.ModelSerializer):
    # This gets the service details inside the item
    service_id = serializers.ReadOnlyField(source='service.id')
    service_name_en = serializers.ReadOnlyField(source='service.name_en')
    service_name_ar = serializers.ReadOnlyField(source='service.name_ar')

    class Meta:
        model = ItemServicePrice
        fields = ['service_id', 'service_name_en',
                  'service_name_ar', 'price', 'percentage']


class ItemListSerializer(serializers.ModelSerializer):
    category_name = serializers.ReadOnlyField(source='category.name_en')
    # We use the 'through' model to show prices per service
    service_prices = ItemServicePriceSerializer(
        source='itemserviceprice_set', many=True, read_only=True)

    class Meta:
        model = Item
        fields = ['id', 'name_en', 'name_ar', 'image',
                  'category', 'category_name', 'service_prices']
