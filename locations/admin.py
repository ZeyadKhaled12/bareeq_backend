from django.contrib import admin
from .models import Location


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    # Added 'get_phone' and 'get_user_role' to make the list more informative
    list_display = ('name', 'user', 'get_phone', 'region', 'get_user_role')
    list_filter = ('region', 'user__profile__role')  # Filter by region or role
    search_fields = ('name', 'user__email', 'user__profile__phone')

    @admin.display(description='Phone Number')
    def get_phone(self, obj):
        if hasattr(obj.user, 'profile'):
            return obj.user.profile.phone
        return "N/A"

    @admin.display(description='Role')
    def get_user_role(self, obj):
        if hasattr(obj.user, 'profile'):
            return obj.user.profile.role
        return "N/A"
