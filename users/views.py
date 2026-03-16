from .models import TimeSlot
from django.db import transaction
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.exceptions import PermissionDenied
from django.contrib.auth import update_session_auth_hash
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema

from .serializers import (
    LoginSerializer,
    CustomerRegistrationSerializer,
    CustomerUpdateSerializer,
    VendorRegisterSerializer,
    VendorProfileSerializer,
    VendorAuthResponseSerializer,
    PasswordChangeSerializer,
    TimeSlot, VendorTimeSlotResponseSerializer, TimeSlotBulkUpdateSerializer
)

# ==========================================
# SECTION: Authentication
# = : Includes Login, Register, and Reset
# ==========================================


class CustomerRegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = CustomerRegistrationSerializer

    @extend_schema(
        tags=['Authentication'],
        responses={201: VendorAuthResponseSerializer},
        summary="Register for customer",
        description="Creates a customer account and returns user data with JWT tokens."
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)

        return Response({
            "user": CustomerRegistrationSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh),
        }, status=status.HTTP_201_CREATED)


class CustomerLoginView(APIView):
    @extend_schema(
        tags=['Authentication'],
        request=LoginSerializer,
        responses={200: VendorAuthResponseSerializer},
        summary="Login for customer",
        description="Login with either email or phone number."
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        refresh = RefreshToken.for_user(user)

        return Response({
            "user": CustomerRegistrationSerializer(user).data,
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        }, status=status.HTTP_200_OK)


@extend_schema(tags=["Authentication"])
class VendorRegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]
    serializer_class = VendorRegisterSerializer

    @extend_schema(
        responses={201: VendorAuthResponseSerializer},
        summary="Register for vendor",
        description="Registers a vendor and returns user details with JWT tokens."
    )
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        refresh = RefreshToken.for_user(user)

        return Response({
            "user": {
                "full_name": user.first_name,
                "email": user.email,
                "phone": user.profile.phone,
            },
            "access": str(refresh.access_token),
            "refresh": str(refresh)
        }, status=status.HTTP_201_CREATED)


class VendorLoginView(APIView):
    @extend_schema(
        tags=['Authentication'],
        request=LoginSerializer,
        responses={200: VendorAuthResponseSerializer},
        summary="Login for vendor",
        description="Login via phone/email and returns user details with JWT tokens."
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data
        refresh = RefreshToken.for_user(user)

        return Response({
            'user': {
                'full_name': user.first_name,
                'email': user.email,
                'phone': user.profile.phone,
            },
            'access': str(refresh.access_token),
            'refresh': str(refresh)
        }, status=status.HTTP_200_OK)


class PasswordChangeView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = PasswordChangeSerializer  # <--- Add this line

    @extend_schema(
        tags=['Authentication'],
        request=PasswordChangeSerializer,
        summary="Reset Password",
        description="Requires current_password, new_password, and confirm_password."
    )
    def post(self, request):
        serializer = PasswordChangeSerializer(
            data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        if not user.check_password(serializer.validated_data.get('current_password')):
            return Response({"error": "كلمة المرور الحالية غير صحيحة"}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(serializer.validated_data.get('new_password'))
        user.save()
        update_session_auth_hash(request, user)
        return Response({"message": "تم تغيير كلمة المرور بنجاح"}, status=status.HTTP_200_OK)


# ==========================================
# SECTION: Customer
# ==========================================

class CustomerProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = CustomerUpdateSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        user = self.request.user
        if hasattr(user, 'profile') and user.profile.role != 'CUSTOMER':
            raise PermissionDenied("This endpoint is reserved for customers.")
        return user

    @extend_schema(tags=['Customer'], summary="Customer Profile Details")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=['Customer'], summary="Update Customer Profile")
    def patch(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @extend_schema(tags=['Customer'], summary="Replace Customer Profile")
    def put(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)


# ==========================================
# SECTION: Vendor
# ==========================================

class VendorProfileView(generics.RetrieveUpdateAPIView):
    serializer_class = VendorProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        user = self.request.user
        if hasattr(user, 'profile') and user.profile.role != 'VENDOR':
            raise PermissionDenied("This endpoint is reserved for vendors.")
        return user

    @extend_schema(tags=['Vendor'], summary="Get Vendor Profile")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=['Vendor'], summary="Update Vendor Profile")
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)

    @extend_schema(tags=['Vendor'], summary="Partial Update Vendor Profile")
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class VendorTimeSlotView(APIView):
    permission_classes = [IsAuthenticated]

    def _handle_update(self, request):
        user = request.user

        if not hasattr(user, 'profile') or user.profile.role != 'VENDOR':
            return Response({"error": "Only vendors can update slots."}, status=status.HTTP_403_FORBIDDEN)

        serializer = TimeSlotBulkUpdateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        days = ['monday', 'tuesday', 'wednesday',
                'thursday', 'friday', 'saturday', 'sunday']

        try:
            with transaction.atomic():
                # Clear all old individual slots for a clean replacement
                TimeSlot.objects.filter(vendor=user).delete()

                new_slots = []
                for day_name in days:
                    day_data = serializer.validated_data.get(day_name, {})
                    for s_type in ['receipt', 'delivery']:
                        items = day_data.get(s_type, [])
                        for item in items:
                            new_slots.append(TimeSlot(
                                vendor=user,
                                day=day_name,
                                slot_type=s_type,
                                # Now mapping to singular 'slot'
                                slot=item.get('slot'),
                                is_free=item.get('is_free', False),
                                unlimit_orders=item.get(
                                    'unlimit_orders', False),
                                limit_orders=item.get('limit_orders', 0),
                                is_close=item.get('is_close', False)
                            ))

                TimeSlot.objects.bulk_create(new_slots)

            return Response({"message": "Time slots updated successfully"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": f"An unexpected error occurred: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @extend_schema(
        tags=['Time Slots'],
        summary="Get Vendor Time Slots",
        responses={200: VendorTimeSlotResponseSerializer}
    )
    def get(self, request):
        if not hasattr(request.user, 'profile') or request.user.profile.role != 'VENDOR':
            return Response({"error": "Unauthorized"}, status=status.HTTP_403_FORBIDDEN)

        serializer = VendorTimeSlotResponseSerializer(request.user)
        return Response(serializer.data)

    @extend_schema(
        tags=['Time Slots'],
        summary="Update All Time Slots (Sync)",
        request=TimeSlotBulkUpdateSerializer,
        responses={200: {"message": "string"}}
    )
    def post(self, request):
        return self._handle_update(request)

    @extend_schema(
        tags=['Time Slots'],
        summary="Replace All Time Slots (PUT)",
        request=TimeSlotBulkUpdateSerializer,
        responses={200: {"message": "string"}}
    )
    def put(self, request):
        return self._handle_update(request)
