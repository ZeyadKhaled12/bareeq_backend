from django.urls import path
from .views import CategoryListView, ItemListView, ServiceListView

urlpatterns = [
    # ... other paths ...
    path('services/', ServiceListView.as_view(), name='service-list'),
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('items/', ItemListView.as_view(), name='item-list'),
]
