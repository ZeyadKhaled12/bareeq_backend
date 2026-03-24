from drf_spectacular.utils import extend_schema, OpenApiTypes
from .permissions import IsVendorEmployee
from .serializers import OrderFinishSerializer, OrderDetailSerializer
from drf_spectacular.utils import extend_schema
from rest_framework.parsers import MultiPartParser, FormParser
from .serializers import ReceiveOrderSerializer, OrderDetailSerializer
from rest_framework import status, permissions
from .serializers import ReceiveOrderSerializer
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import RetrieveUpdateAPIView
from drf_spectacular.utils import extend_schema, OpenApiExample
from rest_framework.generics import CreateAPIView, ListAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter

from .models import Order
from .serializers import OrderCreateSerializer, OrderDetailSerializer, OrderUpdateSerializer, ReceiveOrderSerializer
from .filters import OrderFilter


class OrderPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class CustomerOrderCreateView(CreateAPIView):
    """
    Handles Order Creation for Customers only.
    """
    serializer_class = OrderCreateSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if getattr(self, 'swagger_fake_view', False):
            return []
        return super().get_permissions()

    def check_customer_role(self, user):
        if user.is_superuser:
            return True
        user_role = str(getattr(user, 'role', '')).upper()
        profile_role = ''
        if hasattr(user, 'profile'):
            profile_role = str(getattr(user.profile, 'role', '')).upper()
        return user_role == 'CUSTOMER' or profile_role == 'CUSTOMER'

    @extend_schema(
        tags=['orders'],
        summary="Create Order (Customer Only)",
        description=(
            "Initiates a new order. \n\n"
            "**Required Fields:** \n"
            "- `customer_region`: Region ID for coverage check. \n"
            "- `time_slot_id`: The ID of the slot picked from the public slots API. \n"
            "- `pickup_date`: The specific date for pickup (YYYY-MM-DD)."
        ),
        responses={201: OrderDetailSerializer},
        examples=[
            OpenApiExample(
                'Complete Order Request',
                value={
                    "comment": "Please be on time.",
                    "picked_services": [1, 2],
                    "customer_region": 1,
                    "time_slot_id": 10,
                    "pickup_date": "2026-03-20",
                    "customer_latitude": 30.0444,
                    "customer_longitude": 31.2357
                },
                request_only=True,
            )
        ]
    )
    def post(self, request, *args, **kwargs):
        if not self.check_customer_role(request.user):
            actual_role = getattr(request.user.profile, 'role', 'None') if hasattr(
                request.user, 'profile') else 'None'
            raise PermissionDenied(
                f"Only accounts with the CUSTOMER role can create orders. Your role is: {actual_role}"
            )
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save()


# orders/views.py

# orders/views.py

class UnifiedOrderListView(ListAPIView):
    serializer_class = OrderDetailSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OrderPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = OrderFilter

    def get_queryset(self):
        # 1. Swagger Guard (Stops the terminal errors)
        if getattr(self, "swagger_fake_view", False):
            return Order.objects.none()

        user = self.request.user
        if not user or user.is_anonymous or not hasattr(user, 'profile'):
            return Order.objects.none()

        profile = user.profile
        role = profile.role.upper()

        # Use our property to get the main business ID
        business = profile.business_profile

        if role in ['VENDOR', 'EMPLOYEE']:
            # Vendors and Employees see the same set of orders
            return Order.objects.select_related('customer', 'vendor') \
                                .filter(vendor=business) \
                                .order_by('-created_at')

        elif role == 'CUSTOMER':
            return Order.objects.select_related('customer', 'vendor') \
                                .filter(customer=profile) \
                                .order_by('-created_at')

        if user.is_superuser:
            return Order.objects.all().order_by('-created_at')

        return Order.objects.none()

    @extend_schema(
        tags=['orders'],
        summary="Unified Order List (Customer, Vendor, & Employee)",
        parameters=[
            OpenApiParameter("status", type=str,
                             description="Filter by status"),
            OpenApiParameter("order_key", type=str,
                             description="Search by order ID"),
            OpenApiParameter("date_from", type=str,
                             description="Start date (YYYY-MM-DD)"),
            OpenApiParameter("date_to", type=str,
                             description="End date (YYYY-MM-DD)"),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class CustomerOrderUpdateView(RetrieveUpdateAPIView):
    """
    Allows a customer to view or update their PENDING order.
    customer_region cannot be updated here.
    """
    serializer_class = OrderUpdateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'  # We use the order ID in the URL

    def get_queryset(self):
        user = self.request.user
        profile = getattr(user, 'profile', None)

        if not profile:
            print("DEBUG: User has no profile!")
            return Order.objects.none()

        business = profile.business_profile
        role = profile.role

        print(f"--- DEBUG START ---")
        print(f"Logged in as: {user.username} (Role: {role})")
        print(f"My Profile ID: {profile.id}")
        print(
            f"My Employer ID: {profile.employer_id if role == 'EMPLOYEE' else 'N/A'}")
        print(f"Targeting Business ID: {business.id}")

        # Check how many orders exist for this business ID
        count = Order.objects.filter(vendor=business).count()
        print(f"Orders found for Vendor ID {business.id}: {count}")
        print(f"--- DEBUG END ---")

        return Order.objects.filter(vendor=business).order_by('-created_at')

    @extend_schema(
        tags=['orders'],
        summary="Update Order (Customer Only)",
        description=(
            "Updates an existing order. **Restriction:** Only works if status is 'PENDING'. "
            "The `customer_region` field is locked and cannot be changed."
        ),
        responses={200: OrderDetailSerializer}
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(exclude=True)  # Hide PUT from Swagger to force using PATCH
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)


# orders/views.py


class OrderReceiveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['orders'],
        summary="Receive Order (Finalize Items & Services)",
        description=(
            "Transition an order from PENDING to RECEIVED. \n\n"
            "This endpoint allows the vendor to input the actual items, services, "
            "and set the delivery schedule. It calculates the total price and returns "
            "the full Order model details."
        ),
        request=ReceiveOrderSerializer,
        responses={200: OrderDetailSerializer},
        examples=[
            OpenApiExample(
                'Request Example (Input)',
                value={
                    "delivery_fee": 20.00,
                    "delivery_date": "2026-03-28",
                    "delivery_time_slot_id": 5,
                    "items": [
                        {
                            "item_id": 1,
                            "quantity": 2,
                            "service_ids": [1, 2]
                        }
                    ]
                },
                request_only=True,
            ),
        ]
    )
    def post(self, request, order_id):
        try:
            # 1. Fetch Order
            order = Order.objects.get(id=order_id)
            user_profile = request.user.profile

            # 2. Authorization Check
            if order.vendor != user_profile:
                return Response(
                    {"error": "You are not authorized to receive this order."},
                    status=status.HTTP_403_FORBIDDEN
                )

            # 3. Process receiving logic
            # Passing context={'request': request} is essential for processed_by
            serializer = ReceiveOrderSerializer(
                order,
                data=request.data,
                context={'request': request}
            )

            if serializer.is_valid():
                # This triggers the update() method in ReceiveOrderSerializer
                updated_order = serializer.save()

                # We return serializer.data which, due to to_representation,
                # will use the OrderDetailSerializer format.
                return Response(serializer.data, status=status.HTTP_200_OK)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

# Add this class to your orders/views.py


class OrderMoveToVendorView(APIView):
    """
    Endpoint for Vendors/Employees to move an order from RECEIVED to AT_VENDOR.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['orders'],
        summary="Move Order to Laundry (AT_VENDOR)",
        description="Changes order status from RECEIVED to AT_VENDOR. Only authorized for the assigned Vendor/Employee.",
        responses={200: OrderDetailSerializer}
    )
    def patch(self, request, order_id):
        try:
            # 1. Fetch Order
            order = Order.objects.get(id=order_id)
            user_profile = request.user.profile
            business = user_profile.business_profile  # Uses your profile property

            # 2. Authorization Check (Verify user belongs to the assigned vendor business)
            if order.vendor != business:
                return Response(
                    {"error": "You are not authorized to manage this order."},
                    status=status.HTTP_403_FORBIDDEN
                )

            # 3. Status Transition Validation
            if order.status != 'RECEIVED':
                return Response(
                    {"error": f"Cannot move to AT_VENDOR. Current status is {order.status}."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 4. Perform Update
            order.status = 'AT_VENDOR'
            order.processed_by = user_profile
            order.save()  # This triggers your recalculate_and_invoice logic too

            # 5. Return Full Detail
            serializer = OrderDetailSerializer(
                order, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)


class OrderPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100


class CustomerOrderCreateView(CreateAPIView):
    """
    Handles Order Creation for Customers only.
    """
    serializer_class = OrderCreateSerializer
    permission_classes = [IsAuthenticated]

    def get_permissions(self):
        if getattr(self, 'swagger_fake_view', False):
            return []
        return super().get_permissions()

    def check_customer_role(self, user):
        if user.is_superuser:
            return True
        user_role = str(getattr(user, 'role', '')).upper()
        profile_role = ''
        if hasattr(user, 'profile'):
            profile_role = str(getattr(user.profile, 'role', '')).upper()
        return user_role == 'CUSTOMER' or profile_role == 'CUSTOMER'

    @extend_schema(
        tags=['orders'],
        summary="Create Order (Customer Only)",
        description=(
            "Initiates a new order. \n\n"
            "**Required Fields:** \n"
            "- `customer_region`: Region ID for coverage check. \n"
            "- `time_slot_id`: The ID of the slot picked from the public slots API. \n"
            "- `pickup_date`: The specific date for pickup (YYYY-MM-DD)."
        ),
        responses={201: OrderDetailSerializer},
        examples=[
            OpenApiExample(
                'Complete Order Request',
                value={
                    "comment": "Please be on time.",
                    "picked_services": [1, 2],
                    "customer_region": 1,
                    "time_slot_id": 10,
                    "pickup_date": "2026-03-20",
                    "customer_latitude": 30.0444,
                    "customer_longitude": 31.2357
                },
                request_only=True,
            )
        ]
    )
    def post(self, request, *args, **kwargs):
        if not self.check_customer_role(request.user):
            actual_role = getattr(request.user.profile, 'role', 'None') if hasattr(
                request.user, 'profile') else 'None'
            raise PermissionDenied(
                f"Only accounts with the CUSTOMER role can create orders. Your role is: {actual_role}"
            )
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save()


# orders/views.py

# orders/views.py

class UnifiedOrderListView(ListAPIView):
    serializer_class = OrderDetailSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OrderPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = OrderFilter

    def get_queryset(self):
        # 1. Swagger Guard (Stops the terminal errors)
        if getattr(self, "swagger_fake_view", False):
            return Order.objects.none()

        user = self.request.user
        if not user or user.is_anonymous or not hasattr(user, 'profile'):
            return Order.objects.none()

        profile = user.profile
        role = profile.role.upper()

        # Use our property to get the main business ID
        business = profile.business_profile

        if role in ['VENDOR', 'EMPLOYEE']:
            # Vendors and Employees see the same set of orders
            return Order.objects.select_related('customer', 'vendor') \
                                .filter(vendor=business) \
                                .order_by('-created_at')

        elif role == 'CUSTOMER':
            return Order.objects.select_related('customer', 'vendor') \
                                .filter(customer=profile) \
                                .order_by('-created_at')

        if user.is_superuser:
            return Order.objects.all().order_by('-created_at')

        return Order.objects.none()

    @extend_schema(
        tags=['orders'],
        summary="Unified Order List (Customer, Vendor, & Employee)",
        parameters=[
            OpenApiParameter("status", type=str,
                             description="Filter by status"),
            OpenApiParameter("order_key", type=str,
                             description="Search by order ID"),
            OpenApiParameter("date_from", type=str,
                             description="Start date (YYYY-MM-DD)"),
            OpenApiParameter("date_to", type=str,
                             description="End date (YYYY-MM-DD)"),
        ]
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class CustomerOrderUpdateView(RetrieveUpdateAPIView):
    """
    Allows a customer to view or update their PENDING order.
    customer_region cannot be updated here.
    """
    serializer_class = OrderUpdateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'  # We use the order ID in the URL

    def get_queryset(self):
        user = self.request.user
        profile = getattr(user, 'profile', None)

        if not profile:
            print("DEBUG: User has no profile!")
            return Order.objects.none()

        business = profile.business_profile
        role = profile.role

        print(f"--- DEBUG START ---")
        print(f"Logged in as: {user.username} (Role: {role})")
        print(f"My Profile ID: {profile.id}")
        print(
            f"My Employer ID: {profile.employer_id if role == 'EMPLOYEE' else 'N/A'}")
        print(f"Targeting Business ID: {business.id}")

        # Check how many orders exist for this business ID
        count = Order.objects.filter(vendor=business).count()
        print(f"Orders found for Vendor ID {business.id}: {count}")
        print(f"--- DEBUG END ---")

        return Order.objects.filter(vendor=business).order_by('-created_at')

    @extend_schema(
        tags=['orders'],
        summary="Update Order (Customer Only)",
        description=(
            "Updates an existing order. **Restriction:** Only works if status is 'PENDING'. "
            "The `customer_region` field is locked and cannot be changed."
        ),
        responses={200: OrderDetailSerializer}
    )
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(exclude=True)  # Hide PUT from Swagger to force using PATCH
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)


# orders/views.py


class OrderReceiveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['orders'],
        summary="Receive Order (Finalize Items & Services)",
        description=(
            "Transition an order from PENDING to RECEIVED. \n\n"
            "This endpoint allows the vendor to input the actual items, services, "
            "and set the delivery schedule. It calculates the total price and returns "
            "the full Order model details."
        ),
        request=ReceiveOrderSerializer,
        responses={200: OrderDetailSerializer},
        examples=[
            OpenApiExample(
                'Request Example (Input)',
                value={
                    "delivery_fee": 20.00,
                    "delivery_date": "2026-03-28",
                    "delivery_time_slot_id": 5,
                    "items": [
                        {
                            "item_id": 1,
                            "quantity": 2,
                            "service_ids": [1, 2]
                        }
                    ]
                },
                request_only=True,
            ),
        ]
    )
    def post(self, request, order_id):
        try:
            # 1. Fetch Order
            order = Order.objects.get(id=order_id)
            user_profile = request.user.profile

            # 2. Authorization Check
            if order.vendor != user_profile:
                return Response(
                    {"error": "You are not authorized to receive this order."},
                    status=status.HTTP_403_FORBIDDEN
                )

            # 3. Process receiving logic
            # Passing context={'request': request} is essential for processed_by
            serializer = ReceiveOrderSerializer(
                order,
                data=request.data,
                context={'request': request}
            )

            if serializer.is_valid():
                # This triggers the update() method in ReceiveOrderSerializer
                updated_order = serializer.save()

                # We return serializer.data which, due to to_representation,
                # will use the OrderDetailSerializer format.
                return Response(serializer.data, status=status.HTTP_200_OK)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)

# Add this class to your orders/views.py


class OrderMoveToVendorView(APIView):
    """
    Endpoint for Vendors/Employees to move an order from RECEIVED to AT_VENDOR.
    """
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['orders'],
        summary="Move Order to Laundry (AT_VENDOR)",
        description="Changes order status from RECEIVED to AT_VENDOR. Only authorized for the assigned Vendor/Employee.",
        responses={200: OrderDetailSerializer}
    )
    def patch(self, request, order_id):
        try:
            # 1. Fetch Order
            order = Order.objects.get(id=order_id)
            user_profile = request.user.profile
            business = user_profile.business_profile  # Uses your profile property

            # 2. Authorization Check (Verify user belongs to the assigned vendor business)
            if order.vendor != business:
                return Response(
                    {"error": "You are not authorized to manage this order."},
                    status=status.HTTP_403_FORBIDDEN
                )

            # 3. Status Transition Validation
            if order.status != 'RECEIVED':
                return Response(
                    {"error": f"Cannot move to AT_VENDOR. Current status is {order.status}."},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # 4. Perform Update
            order.status = 'AT_VENDOR'
            order.processed_by = user_profile
            order.save()  # This triggers your recalculate_and_invoice logic too

            # 5. Return Full Detail
            serializer = OrderDetailSerializer(
                order, context={'request': request})
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=status.HTTP_404_NOT_FOUND)


class OrderFinishView(APIView):
    permission_classes = [IsVendorEmployee]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        tags=['orders'],
        summary="Finish Order (Upload Photos from Device)",
        description=(
            "Moves order to FINISHED. \n\n"
            "**In Swagger UI:** \n"
            "1. Click 'Add Item' for `items_data`. \n"
            "2. Enter the `item_id`. \n"
            "3. Click 'Add Item' for `photos`. \n"
            "4. You will see a **Choose File** button appear."
        ),
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'items_data': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'item_id': {'type': 'integer'},
                                'photos': {
                                    'type': 'array',
                                    'items': {
                                        'type': 'string',
                                        'format': 'binary'  # This forces the "Choose File" button
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
        responses={200: OrderDetailSerializer}
    )
    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)

            if order.vendor != request.user.profile.business_profile:
                return Response({"error": "Unauthorized vendor access."}, status=403)

            serializer = OrderFinishSerializer(
                data=request.data,
                context={'request': request, 'order': order}
            )

            if serializer.is_valid():
                updated_order = serializer.save()
                return Response(
                    OrderDetailSerializer(updated_order, context={
                                          'request': request}).data,
                    status=200
                )
            return Response(serializer.errors, status=400)

        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)
