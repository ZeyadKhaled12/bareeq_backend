from .models import Region
from django.contrib import admin
from .models import Gender


@admin.register(Gender)
class GenderAdmin(admin.ModelAdmin):
    list_display = ('id', 'name_en', 'name_ar')

@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name_en', 'name_ar')
