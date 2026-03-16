from django.urls import path
from .views import (
    CustomerLoginView, VendorLoginView,
    CustomerRegisterView, VendorRegisterView,
    CustomerProfileView, VendorProfileView,
    PasswordChangeView, VendorTimeSlotView
)

urlpatterns = [
    # Authentication & Registration
    path('customer/login/', CustomerLoginView.as_view(), name='customer-login'),
    path('customer/register/', CustomerRegisterView.as_view(),
         name='customer-register'),
    path('vendor/login/', VendorLoginView.as_view(), name='vendor-login'),
    path('vendor/register/', VendorRegisterView.as_view(), name='vendor-register'),
    path('password/change/', PasswordChangeView.as_view(), name='password-change'),

    # Profile Operations
    path('customer/profile/', CustomerProfileView.as_view(),
         name='customer-profile'),
    path('vendor/profile/', VendorProfileView.as_view(), name='vendor-profile'),
    path('vendor/time-slots/', VendorTimeSlotView.as_view(),
         name='vendor-time-slots'),
]
