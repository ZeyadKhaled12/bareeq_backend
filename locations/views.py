from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from .models import Location
from .serializers import LocationSerializer


@extend_schema(tags=["Locations"])
class LocationListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LocationSerializer

    def get_queryset(self):
        """
        Returns all locations belonging to the authenticated user.
        Includes a check for Swagger to prevent crashes during schema generation.
        """
        # FIX: Check if this is a documentation generation request
        if getattr(self, 'swagger_fake_view', False):
            return Location.objects.none()

        return Location.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @extend_schema(
        summary="List saved locations",
        description="Retrieve all locations you have saved to your profile."
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(
        summary="Create a new location",
        description="Add a new address (e.g., Home, Work) and link it to a specific Cairo region."
    )
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


@extend_schema(tags=["Locations"])
class LocationDetailView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = LocationSerializer

    def get_queryset(self):
        # FIX: Check if this is a documentation generation request
        if getattr(self, 'swagger_fake_view', False):
            return Location.objects.none()

        return Location.objects.filter(user=self.request.user)

    @extend_schema(summary="Get a specific location detail")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(summary="Update a specific location")
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(summary="Partially update a specific location")
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(summary="Delete a location")
    def delete(self, request, *args, **kwargs):
        return super().delete(request, *args, **kwargs)
