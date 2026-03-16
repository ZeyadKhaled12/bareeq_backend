from .serializers import RegionSerializer
from .models import Region, Gender
from rest_framework import generics
from rest_framework.response import Response
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView


class GenderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Gender
        fields = ['id', 'name_ar', 'name_en']


class GenderListView(generics.ListAPIView):
    queryset = Gender.objects.all()
    serializer_class = GenderSerializer


class MyProtectedView(APIView):
    # This blocks users without a valid token
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response({"message": "You are authorized!"})


# lists/views.py


class RegionListView(generics.ListAPIView):
    queryset = Region.objects.all()
    serializer_class = RegionSerializer
    # Usually, lists like these are public, so we don't strictly need IsAuthenticated
    permission_classes = []
