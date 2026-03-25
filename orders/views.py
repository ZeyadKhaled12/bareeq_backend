from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView, ListAPIView, RetrieveUpdateAPIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import PermissionDenied
from rest_framework.pagination import PageNumberPagination
from rest_framework.parsers import MultiPartParser, FormParser

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiParameter, OpenApiTypes

from .models import Order
from .permissions import IsVendorEmployee
from .filters import OrderFilter
from .serializers import (
    OrderCreateSerializer,
    OrderDetailSerializer,
    OrderUpdateSerializer,
    ReceiveOrderSerializer,
    OrderFinishSerializer
)

# --- Utils ---


class OrderPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

# --- Views ---


class CustomerOrderCreateView(CreateAPIView):
    """ Handles Order Creation for Customers only. """
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
        responses={201: OrderDetailSerializer}
    )
    def post(self, request, *args, **kwargs):
        if not self.check_customer_role(request.user):
            actual_role = getattr(request.user.profile, 'role', 'None') if hasattr(
                request.user, 'profile') else 'None'
            raise PermissionDenied(
                f"Only accounts with the CUSTOMER role can create orders. Your role is: {actual_role}")
        return super().post(request, *args, **kwargs)

    def perform_create(self, serializer):
        serializer.save()


class UnifiedOrderListView(ListAPIView):
    serializer_class = OrderDetailSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OrderPagination
    filter_backends = [DjangoFilterBackend]
    filterset_class = OrderFilter

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return Order.objects.none()

        user = self.request.user
        if not user or user.is_anonymous or not hasattr(user, 'profile'):
            return Order.objects.none()

        profile = user.profile
        role = profile.role.upper()
        business = profile.business_profile

        if role in ['VENDOR', 'EMPLOYEE']:
            return Order.objects.select_related('customer', 'vendor').filter(vendor=business).order_by('-created_at')
        elif role == 'CUSTOMER':
            return Order.objects.select_related('customer', 'vendor').filter(customer=profile).order_by('-created_at')

        return Order.objects.all().order_by('-created_at') if user.is_superuser else Order.objects.none()

    @extend_schema(tags=['orders'], summary="Unified Order List")
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class CustomerOrderUpdateView(RetrieveUpdateAPIView):
    serializer_class = OrderUpdateSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'id'

    def get_queryset(self):
        profile = getattr(self.request.user, 'profile', None)
        if not profile:
            return Order.objects.none()
        return Order.objects.filter(vendor=profile.business_profile).order_by('-created_at')

    @extend_schema(tags=['orders'], summary="Update Order (Customer Only)")
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)

    @extend_schema(exclude=True)
    def put(self, request, *args, **kwargs):
        return super().put(request, *args, **kwargs)


class OrderReceiveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(
        tags=['orders'],
        summary="Receive Order (Finalize Items & Services)",
        request=ReceiveOrderSerializer,
        responses={200: OrderDetailSerializer}
    )
    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)
            if order.vendor != request.user.profile:
                return Response({"error": "Unauthorized"}, status=403)
            serializer = ReceiveOrderSerializer(
                order, data=request.data, context={'request': request})
            if serializer.is_valid():
                updated_order = serializer.save()
                return Response(serializer.data, status=200)
            return Response(serializer.errors, status=400)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)


class OrderMoveToVendorView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(tags=['orders'], summary="Move Order to Laundry (AT_VENDOR)")
    def patch(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)
            if order.vendor != request.user.profile.business_profile:
                return Response({"error": "Unauthorized"}, status=403)

            if order.status != 'RECEIVED':
                return Response({"error": f"Invalid status: {order.status}"}, status=400)

            order.status = 'AT_VENDOR'
            order.processed_by = request.user.profile
            order.save()
            return Response(OrderDetailSerializer(order, context={'request': request}).data)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)


class OrderFinishView(APIView):
    permission_classes = [IsVendorEmployee]
    parser_classes = [MultiPartParser, FormParser]

    @extend_schema(
        tags=['orders'],
        summary="Finish Order (Upload Photos)",
        description=(
            "Upload photos for items to finish the order. \n\n"
            "**Note:** To see the file upload buttons in Swagger, ensure you select "
            "'multipart/form-data' in the 'Request body' dropdown if it isn't selected."
        ),
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'items_data': {
                        'type': 'string',
                        'description': 'JSON string containing item_id and photo mappings. Example: [{"item_id": 1}]',
                    },
                    'photos': {
                        'type': 'array',
                        'items': {'type': 'string', 'format': 'binary'},
                        'description': 'Select multiple files here'
                    }
                }
            }
        },
        responses={200: OrderDetailSerializer}
    )
    def post(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)
            user_profile = request.user.profile
            user_business = user_profile.business_profile

            # DEBUGGING: Look at your terminal when you hit the API
            print(f"DEBUG: Order Vendor ID: {order.vendor.id}")
            print(f"DEBUG: Logged-in Business ID: {user_business.id}")
            print(f"DEBUG: User Role: {user_profile.role}")

            if order.vendor != user_business:
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


class OrderDeliverView(APIView):
    permission_classes = [IsVendorEmployee]

    @extend_schema(
        tags=['orders'],
        summary="Deliver Order (RETURNED)",
        description="Switch status from FINISHED to RETURNED when customer picks up items.",
        responses={200: OrderDetailSerializer}
    )
    def patch(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)

            # Authorization check
            if order.vendor != request.user.profile.business_profile:
                return Response({"error": "Unauthorized"}, status=403)

            # Business Logic: Can only deliver if it's finished
            if order.status != 'FINISHED':
                return Response(
                    {"error": f"Cannot deliver order in {order.status} status. Must be FINISHED."},
                    status=400
                )

            order.status = 'RETURNED'
            order.save()

            return Response(OrderDetailSerializer(order, context={'request': request}).data)
        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)


class OrderPayInvoiceView(APIView):
    permission_classes = [IsVendorEmployee]

    @extend_schema(
        tags=['orders'],
        summary="Mark Invoice as Paid",
        description="Sets 'is_paid' to true for the order's invoice.",
        responses={200: {"message": "Invoice marked as paid"}}
    )
    def patch(self, request, order_id):
        try:
            order = Order.objects.get(id=order_id)

            if order.vendor != request.user.profile.business_profile:
                return Response({"error": "Unauthorized"}, status=403)

            # Access the related invoice
            invoice = order.invoice
            if invoice.is_paid:
                return Response({"message": "Invoice is already paid."}, status=200)

            invoice.is_paid = True
            invoice.save()

            return Response({
                "message": "Invoice marked as paid successfully.",
                "invoice_number": invoice.invoice_number,
                "is_paid": invoice.is_paid
            }, status=200)

        except Order.DoesNotExist:
            return Response({"error": "Order not found"}, status=404)
        except Exception as e:
            return Response({"error": "Invoice not found for this order."}, status=404)


class CustomerOrderCancelView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=['orders'],
        summary="Cancel Order (Customer Only)",
        description="Allows a customer to cancel their own order only if it is still PENDING.",
        responses={200: {"message": "Order canceled successfully"},
                   400: {"error": "Reason"}}
    )
    def patch(self, request, order_id):
        try:
            # Look for the order belonging specifically to this customer
            order = Order.objects.get(
                id=order_id, customer=request.user.profile)

            # Check if it's already canceled or moved past pending
            if order.status == 'CANCELED':
                return Response({"error": "Order is already canceled."}, status=400)

            if order.status != 'PENDING':
                return Response(
                    {"error": f"Cannot cancel order. Current status is {order.status}. "
                     "Only PENDING orders can be canceled."},
                    status=400
                )

            order.status = 'CANCELED'
            order.save()

            return Response({"message": "Order has been canceled successfully."}, status=200)

        except Order.DoesNotExist:
            return Response({"error": "Order not found or you do not have permission to cancel it."}, status=404)
