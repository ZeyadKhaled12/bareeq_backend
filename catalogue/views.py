from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny  # <--- Change this
from drf_spectacular.utils import extend_schema
from .models import Service
from .serializers import ServiceListSerializer


class ServiceListView(ListAPIView):
    queryset = Service.objects.all()
    serializer_class = ServiceListSerializer
    # This makes the API public (no Token/Session required)
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['lists'],
        summary="Get All Available Services",
        description="Public API to return all services. No authentication required.",
        responses={200: ServiceListSerializer(many=True)}
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
