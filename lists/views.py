from rest_framework import generics, serializers, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db.models import Exists, OuterRef

from .models import Region, Gender
from .serializers import RegionSerializer
# Import the Location model from your locations app
from locations.models import Location


class GenderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gender
        fields = ['id', 'name_ar', 'name_en']


class GenderListView(generics.ListAPIView):
    queryset = Gender.objects.all()
    serializer_class = GenderSerializer


class MyProtectedView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"message": "You are authorized!"})


class RegionListView(generics.ListAPIView):
    serializer_class = RegionSerializer
    permission_classes = []

    def get_queryset(self):
        """
        Annotates each region with 'is_avail'. 
        It returns True if a Location exists for that region.
        """
        # Create a subquery that looks for any location matching the current region ID
        vendor_locations = Location.objects.filter(region=OuterRef('pk'))

        # Return regions with the dynamic is_avail field
        return Region.objects.all().annotate(
            is_avail=Exists(vendor_locations)
        )
