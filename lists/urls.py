from django.urls import path
from .views import GenderListView, RegionListView

urlpatterns = [
    # Path for getting the list of Genders
    # URL will be: /api/lists/genders/
    path('genders/', GenderListView.as_view(), name='gender-list'),
    path('regions/cairo/', RegionListView.as_view(), name='cairo-regions'),

    # You can add more list endpoints here later, for example:
    # path('cities/', CityListView.as_view(), name='city-list'),
]
