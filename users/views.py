# Assume UserProfileSerializer exists
from orders.models import Order

from .serializers import CustomerLoginSerializer, EmployeeCreateSerializer, UserProfileSerializer, VendorTimeSlotSerializer, VendorTimeSlotResponseSerializer
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import ListCreateAPIView
from rest_framework.permissions import AllowAny
from .serializers import VendorTimeSlotSerializer
from .models import TimeSlot, UserProfile
from locations.models import Location
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework import status
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
        request=CustomerLoginSerializer,  # <--- Check if this comma is here
        # <--- And check this one!
        responses={200: VendorAuthResponseSerializer},
        summary="Login for customer",
        description="Login with either email or phone number."
    )
    def post(self, request):
        serializer = CustomerLoginSerializer(data=request.data)
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
        summary="Login for Vendor & Employee",
        description="Login via phone/email. Returns user details and role (VENDOR or EMPLOYEE)."
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data

        profile = user.profile
        refresh = RefreshToken.for_user(user)

        return Response({
            'user': {
                'full_name': user.first_name,
                'email': user.email,
                'phone': profile.phone,
                'role': profile.role,  # Returns 'VENDOR' or 'EMPLOYEE'
                # Optional: Include employer name if they are an employee
                'business_name': profile.business_profile.user.first_name if profile.role == 'EMPLOYEE' else user.first_name
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
                # Delete old slots for this vendor
                TimeSlot.objects.filter(vendor=user).delete()

                new_slots = []
                for day_name in days:
                    # Get the day data (e.g., 'monday': {'receipt': [], 'delivery': []})
                    day_data = serializer.validated_data.get(day_name, {})

                    for s_type in ['receipt', 'delivery']:
                        items = day_data.get(s_type, [])
                        for item in items:
                            new_slots.append(TimeSlot(
                                vendor=user,
                                day=day_name,
                                slot_type=s_type,
                                slot=item.get('slot'),
                                is_free=item.get('is_free', False),
                                unlimit_orders=item.get(
                                    'unlimit_orders', False),
                                limit_orders=item.get('limit_orders', 0),
                                is_close=item.get('is_close', False)
                            ))

                if new_slots:
                    TimeSlot.objects.bulk_create(new_slots)

            # Return the fresh data so the UI updates automatically
            return Response(VendorTimeSlotResponseSerializer(user).data, status=status.HTTP_200_OK)

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
        summary="Update All Time Slots",
        request=TimeSlotBulkUpdateSerializer,
        responses={200: VendorTimeSlotResponseSerializer}
    )
    def post(self, request):
        return self._handle_update(request)

    @extend_schema(
        tags=['Time Slots'],
        summary="Replace All Time Slots (PUT)",
        request=TimeSlotBulkUpdateSerializer,
        responses={200: VendorTimeSlotResponseSerializer}
    )
    def put(self, request):
        return self._handle_update(request)


class VendorSlotsByRegionView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=['Time Slots'],
        summary="Public Time Slots",
        description=(
            "Finds the vendor assigned to a region and returns their schedule. "
            "**Required:** Provide a `date` to see which slots are full (`is_full: true`) "
            "based on the vendor's order limits for that specific day."
        ),
        parameters=[
            OpenApiParameter(
                name="region_id",
                type=int,
                location=OpenApiParameter.QUERY,
                required=True,
                description="The ID of the region (e.g., 1)."
            ),
            OpenApiParameter(
                name="date",
                type=str,
                location=OpenApiParameter.QUERY,
                required=True,
                description="The date to check (Format: YYYY-MM-DD). Example: 2026-03-25"
            )
        ],
        responses={
            200: VendorTimeSlotResponseSerializer,
            404: {"detail": "This region is not covered by any vendor."}
        }
    )
    def get(self, request):
        region_id = request.query_params.get('region_id')
        target_date = request.query_params.get('date')

        # Basic validation
        if not region_id or not target_date:
            return Response(
                {"error": "Both region_id and date (YYYY-MM-DD) are required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Logic to find vendor
        vendor_location = Location.objects.filter(
            region_id=region_id,
            user__profile__role='VENDOR'
        ).select_related('user').first()

        if not vendor_location:
            return Response(
                {"message": "No vendor covers this region."},
                status=status.HTTP_404_NOT_FOUND
            )

        # Pass the date to the serializer context so 'is_full' can be calculated
        serializer = VendorTimeSlotResponseSerializer(
            vendor_location.user,
            context={'target_date': target_date}
        )
        return Response(serializer.data)


# users/views.py

class VendorEmployeeManagementView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.request.method == 'POST':
            return EmployeeCreateSerializer
        return UserProfileSerializer

    def get_queryset(self):
        # 1. Swagger Guard
        if getattr(self, "swagger_fake_view", False):
            return UserProfile.objects.none()

        user = self.request.user

        # 2. Check if user is authenticated and has a profile
        if not user or user.is_anonymous or not hasattr(user, 'profile'):
            return UserProfile.objects.none()

        # 3. Return the Employees that belong to this Vendor
        return UserProfile.objects.select_related('user').filter(
            employer=user.profile,
            role='EMPLOYEE'
        )

    def check_vendor_role(self, user):
        return hasattr(user, 'profile') and user.profile.role == 'VENDOR'

    @extend_schema(
        tags=['Employee Management'],
        summary="Create Employee (Vendor Only)",
        description="Allows a Vendor to create an account for their employee."
    )
    def post(self, request, *args, **kwargs):
        if not self.check_vendor_role(request.user):
            return Response({"error": "Only Vendors can create employees."}, status=403)
        return super().post(request, *args, **kwargs)

    @extend_schema(
        tags=['Employee Management'],
        summary="List My Employees",
        description="Returns a list of all employees created by this Vendor."
    )
    def get(self, request, *args, **kwargs):
        if not self.check_vendor_role(request.user):
            return Response({"error": "Access denied."}, status=403)
        return super().get(request, *args, **kwargs)
