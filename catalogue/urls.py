from django.urls import path
from .views import ServiceListView

urlpatterns = [
    # ... other paths ...
    path('services/', ServiceListView.as_view(), name='all-services-list'),
]
