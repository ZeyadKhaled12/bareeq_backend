from django.urls import path
from .views import CustomerOrderCreateView, OrderFinishView, OrderMoveToVendorView, OrderReceiveView, UnifiedOrderListView, CustomerOrderUpdateView

urlpatterns = [
    path('create/', CustomerOrderCreateView.as_view(), name='order-create'),
    path('list/', UnifiedOrderListView.as_view(), name='order-list'),
    path('update/<int:id>/', CustomerOrderUpdateView.as_view(), name='order-update'),
    path('receive/<int:order_id>/',
         OrderReceiveView.as_view(), name='order-receive'),
    path('<int:order_id>/move-to-vendor/',
         OrderMoveToVendorView.as_view(), name='order-move-to-vendor'),
    path('<int:order_id>/finish/', OrderFinishView.as_view(), name='order-finish'),
]
