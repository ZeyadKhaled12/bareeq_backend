from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiParameter
from .models import Service, Category, Item
from .serializers import ServiceListSerializer, CategoryListSerializer, ItemListSerializer


class ServiceListView(ListAPIView):
    queryset = Service.objects.all()
    serializer_class = ServiceListSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Items'],
        summary="1. Get All Services",
        description="Returns a list of all available services (e.g., Wash, Dry Clean)."
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class CategoryListView(ListAPIView):
    queryset = Category.objects.all()
    serializer_class = CategoryListSerializer
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Items'],
        summary="2. Get All Categories",
        description="Returns all categories (e.g., Men, Women, Home)."
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ItemListView(ListAPIView):
    serializer_class = ItemListSerializer
    permission_classes = [AllowAny]

    def get_queryset(self):
        queryset = Item.objects.select_related('category').prefetch_related(
            'itemserviceprice_set__service').all()

        category_id = self.request.query_params.get('category')
        service_id = self.request.query_params.get('service')

        if category_id:
            queryset = queryset.filter(category_id=category_id)

        if service_id:
            # Filter items that have a price record for the specific service
            queryset = queryset.filter(itemserviceprice__service_id=service_id)

        return queryset.distinct()

    @extend_schema(
        tags=['Items'],
        summary="3. Get All Items (with Filters)",
        description="Returns items. Filter by ?category=ID or ?service=ID.",
        parameters=[
            OpenApiParameter(
                name='category', description='Filter by Category ID', required=False, type=int),
            OpenApiParameter(
                name='service', description='Filter by Service ID', required=False, type=int),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
