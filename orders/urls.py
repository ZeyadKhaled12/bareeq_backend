from django.urls import path
from .views import CustomerOrderCancelView, CustomerOrderCreateView, OrderDeliverView, OrderFinishView, OrderMoveToVendorView, OrderPayInvoiceView, OrderReceiveView, UnifiedOrderListView, CustomerOrderUpdateView

urlpatterns = [
    path('create/', CustomerOrderCreateView.as_view(), name='order-create'),
    path('list/', UnifiedOrderListView.as_view(), name='order-list'),
    path('update/<int:id>/', CustomerOrderUpdateView.as_view(), name='order-update'),
    path('receive/<int:order_id>/',
         OrderReceiveView.as_view(), name='order-receive'),
    path('<int:order_id>/move-to-vendor/',
         OrderMoveToVendorView.as_view(), name='order-move-to-vendor'),
    path('<int:order_id>/finish/', OrderFinishView.as_view(), name='order-finish'),
    path('api/orders/<int:order_id>/deliver/',
         OrderDeliverView.as_view(), name='order-deliver'),
    path('api/orders/<int:order_id>/pay/',
         OrderPayInvoiceView.as_view(), name='order-pay'),
    path('api/orders/<int:order_id>/cancel/',
         CustomerOrderCancelView.as_view(), name='order-cancel'),
]
