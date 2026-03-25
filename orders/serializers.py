from .models import OrderItem
import json

from .models import Order, OrderItem
from .models import OrderItem, Order
import uuid
from decimal import Decimal
from django.db import transaction
from rest_framework import serializers

# Models
from .models import Invoice, Order, OrderItem, SelectedService
from catalogue.models import Item, ItemServicePrice, Service
from users.models import TimeSlot, UserProfile
from locations.models import Location
from lists.models import Region

# Foreign Serializers
from users.serializers import TimeSlotItemSerializer

# --- 1. RESPONSE HELPERS (Nested Data) ---


class InvoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Invoice
        fields = ['invoice_number', 'subtotal', 'vat_amount',
                  'delivery_charge', 'total_amount', 'is_paid', 'issued_at']


class OrderItemDetailSerializer(serializers.Serializer):
    """
    Formats the grouped items for the frontend.
    Example: { "item": {...}, "services": [...], "quantity": 2 }
    """
    item = serializers.SerializerMethodField()
    services = serializers.SerializerMethodField()
    quantity = serializers.IntegerField()

    def get_item(self, obj_data):
        item = obj_data['item_instance']
        return {
            "id": item.id,
            "name_en": item.name_en,
            "name_ar": item.name_ar,
            "image": item.image.url if item.image else None
        }

    def get_services(self, obj_data):
        return obj_data['services_list']


# --- 2. THE MAIN DETAIL SERIALIZER (The "New One") ---

class OrderDetailSerializer(serializers.ModelSerializer):
    order_key = serializers.SerializerMethodField()
    items = serializers.SerializerMethodField()
    invoice = InvoiceSerializer(read_only=True)  # Nested Invoice
    pick_up_time_slot = TimeSlotItemSerializer(
        source='time_slot', read_only=True)
    delivery_time_slot = TimeSlotItemSerializer(read_only=True)

    class Meta:
        model = Order
        fields = [
            'id', 'order_key', 'barcode', 'status',
            'invoice',  # Replaces delivery_fee and total_price
            'items', 'pickup_date', 'delivery_date',
            'pick_up_time_slot', 'delivery_time_slot', 'created_at'
        ]

    def get_order_key(self, obj):
        # Fix for NULL: If barcode is empty string, return a fallback or generate one
        if not obj.barcode:
            return "#PENDING"
        return f"#{obj.barcode.replace('-', '')}"

    def get_items(self, obj):
        results = []
        groups = {}
        for order_item in obj.items.all():
            service_qs = order_item.selected_services.all()
            service_ids = tuple(sorted(service_qs.values_list(
                'item_service_price__service_id', flat=True)))
            group_key = (order_item.item_type.id, service_ids)

            if group_key not in groups:
                services_data = [
                    {
                        "id": s.item_service_price.service.id,
                        "name_en": s.item_service_price.service.name_en,
                        "price": str(s.item_service_price.price)
                    } for s in service_qs
                ]
                groups[group_key] = {
                    "item_instance": order_item.item_type,
                    "services_list": services_data,
                    "quantity": 1
                }
            else:
                groups[group_key]["quantity"] += 1

        for key in groups:
            results.append(OrderItemDetailSerializer(groups[key]).data)
        return results


# --- 3. CREATION & UPDATE SERIALIZERS ---

class OrderCreateSerializer(serializers.ModelSerializer):
    """Used by Customers to place a new request."""
    time_slot_id = serializers.PrimaryKeyRelatedField(
        queryset=TimeSlot.objects.all(), source='time_slot'
    )
    customer_region = serializers.PrimaryKeyRelatedField(
        queryset=Region.objects.all())

    class Meta:
        model = Order
        fields = [
            'comment', 'picked_services', 'customer_region',
            'customer_latitude', 'customer_longitude',
            'time_slot_id', 'pickup_date'
        ]

    def create(self, validated_data):
        user_profile = self.context['request'].user.profile
        region = validated_data.get('customer_region')

        # Find vendor assigned to this region
        vendor_loc = Location.objects.filter(region=region).first()
        vendor_profile = UserProfile.objects.get(
            user=vendor_loc.user) if vendor_loc else None

        picked_services = validated_data.pop('picked_services', [])
        order = Order.objects.create(
            customer=user_profile,
            vendor=vendor_profile,
            status='PENDING',
            **validated_data
        )
        if picked_services:
            order.picked_services.set(picked_services)
        return order

    def to_representation(self, instance):
        return OrderDetailSerializer(instance, context=self.context).data


class OrderUpdateSerializer(serializers.ModelSerializer):
    """Used to modify PENDING orders only."""
    time_slot_id = serializers.PrimaryKeyRelatedField(
        queryset=TimeSlot.objects.all(), source='time_slot', required=False
    )

    class Meta:
        model = Order
        fields = [
            'comment', 'picked_services', 'time_slot_id',
            'pickup_date', 'customer_latitude', 'customer_longitude'
        ]

    def validate(self, data):
        if self.instance.status != 'PENDING':
            raise serializers.ValidationError(
                "Only PENDING orders can be updated.")
        return data

    def to_representation(self, instance):
        return OrderDetailSerializer(instance, context=self.context).data


# --- 4. RECEIVE ORDER SERIALIZERS (Vendor Action) ---

class OrderItemInputSerializer(serializers.Serializer):
    """Input helper for receiving specific items and services."""
    item_id = serializers.PrimaryKeyRelatedField(
        queryset=Item.objects.all(), source='item_type'
    )
    quantity = serializers.IntegerField(min_value=1)
    service_ids = serializers.ListField(
        child=serializers.IntegerField(), min_length=1
    )

    def validate(self, data):
        item = data['item_type']
        service_ids = data['service_ids']
        price_records = ItemServicePrice.objects.filter(
            item=item, service_id__in=service_ids)

        if price_records.count() != len(service_ids):
            raise serializers.ValidationError(
                f"Invalid services for item {item.id}")

        data['price_records'] = price_records
        return data


class ReceiveOrderSerializer(serializers.ModelSerializer):
    """
    Used by the Vendor to input received laundry.
    Triggers recalculation and Invoice creation via instance.save().
    """
    items = OrderItemInputSerializer(many=True, write_only=True)
    delivery_time_slot_id = serializers.PrimaryKeyRelatedField(
        queryset=TimeSlot.objects.all(), source='delivery_time_slot'
    )

    class Meta:
        model = Order
        fields = ['items', 'delivery_fee',
                  'delivery_time_slot_id', 'delivery_date']

    def update(self, instance, validated_data):
        items_data = validated_data.pop('items')

        with transaction.atomic():
            # 1. Clean slate for items
            instance.items.all().delete()

            # 2. Add new items with tags
            for entry in items_data:
                item_type = entry['item_type']
                price_records = entry['price_records']

                for i in range(entry['quantity']):
                    order_item = OrderItem.objects.create(
                        order=instance,
                        item_type=item_type,
                        tag_code=f"{instance.barcode}-{uuid.uuid4().hex[:4].upper()}"
                    )
                    for pr in price_records:
                        SelectedService.objects.create(
                            order_item=order_item,
                            item_service_price=pr
                        )

            # 3. Update top-level info
            instance.delivery_fee = validated_data.get('delivery_fee')
            instance.delivery_time_slot = validated_data.get(
                'delivery_time_slot')
            instance.delivery_date = validated_data.get('delivery_date')
            instance.status = 'RECEIVED'

            if 'request' in self.context:
                instance.processed_by = self.context['request'].user.profile

            # 4. Save triggers the math logic and invoice creation in the model
            instance.save()

        return instance

    def to_representation(self, instance):
        return OrderDetailSerializer(instance, context=self.context).data

# orders/serializers.py


class OrderStatusUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['status']

    def validate_status(self, value):
        if self.instance.status != 'RECEIVED':
            raise serializers.ValidationError(
                f"Cannot move to AT_VENDOR. Current status is {self.instance.status}."
            )
        if value != 'AT_VENDOR':
            raise serializers.ValidationError(
                "This endpoint is specifically for moving to AT_VENDOR.")
        return value

    def to_representation(self, instance):
        # Return the full order detail after update
        return OrderDetailSerializer(instance, context=self.context).data


class OrderFinishItemSerializer(serializers.Serializer):
    item_id = serializers.IntegerField()
    # Ensure this is ImageField, NOT CharField or FileField
    photos = serializers.ListField(
        child=serializers.ImageField()
    )


class OrderFinishSerializer(serializers.Serializer):
    items_data = serializers.JSONField()

    def to_internal_value(self, data):
        # Handle Swagger/MultiPart string issue
        if 'items_data' in data and isinstance(data['items_data'], str):
            try:
                if hasattr(data, 'dict'):
                    data = data.dict()
                else:
                    data = dict(data)
                data['items_data'] = json.loads(data['items_data'])
            except json.JSONDecodeError:
                raise serializers.ValidationError(
                    {"items_data": "Invalid JSON format."})
        return super().to_internal_value(data)

    def validate(self, attrs):
        order = self.context.get('order')
        items_data = attrs.get('items_data', [])

        # Look for 'item_type_id' (the catalog ID) inside this order's items
        valid_catalog_ids = list(
            order.items.values_list('item_type_id', flat=True))

        provided_ids = [item.get('item_id') for item in items_data]

        for oid in provided_ids:
            if oid not in valid_catalog_ids:
                raise serializers.ValidationError(
                    f"Item ID {oid} is not part of Order #{order.id}. "
                    f"Valid Item IDs in this order are: {valid_catalog_ids}"
                )

        return attrs

    def save(self):
        order = self.context.get('order')
        # This matches the 'photos' array from your Swagger/Request
        photos = self.context['request'].FILES.getlist('photos')
        items_data = self.validated_data['items_data']

        # Map photos to OrderItems based on item_type_id
        for index, entry in enumerate(items_data):
            catalog_id = entry.get('item_id')
            # Find the specific OrderItem record
            order_item = order.items.filter(item_type_id=catalog_id).first()

            if order_item and index < len(photos):
                order_item.photo_finished = photos[index]
                order_item.save()

        # Update order status
        order.status = 'FINISHED'
        order.save()
        return order
