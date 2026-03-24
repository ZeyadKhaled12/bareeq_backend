from django_filters import rest_framework as filters
from .models import Order
from django.db.models import Q


class OrderFilter(filters.FilterSet):
    # Status filter (Exact match)
    status = filters.CharFilter(field_name="status", lookup_expr='iexact')

    # Date Range filters
    date_from = filters.DateFilter(field_name="created_at", lookup_expr='gte')
    date_to = filters.DateFilter(field_name="created_at", lookup_expr='lte')

    # Custom Search for order_key (e.g., #ORD7D2F1A)
    # We strip the '#' and '-' to match the stored barcode
    order_key = filters.CharFilter(method='filter_order_key')

    class Meta:
        model = Order
        fields = ['status', 'date_from', 'date_to', 'order_key']

    def filter_order_key(self, queryset, name, value):
        # Remove common prefix symbols if the user types them
        clean_value = value.replace('#', '').replace('-', '').upper()
        # Search for the cleaned value inside the barcode field
        return queryset.filter(barcode__icontains=clean_value)
