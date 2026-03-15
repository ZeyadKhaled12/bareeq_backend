from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from .models import UserProfile

# 1. Create an Inline for the Profile


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = 'بيانات الملف الشخصي (Profile Data)'
    fk_name = 'user'

# 2. Define a new UserAdmin


class UserAdmin(BaseUserAdmin):
    inlines = (UserProfileInline, )
    list_display = ('username', 'email', 'get_role',
                    'get_employer', 'is_staff')
    list_filter = ('profile__role', 'is_staff', 'is_superuser')

    # Helper functions to show Profile data in the main list
    def get_role(self, instance):
        return instance.profile.get_role_display()
    get_role.short_description = 'الرتبة (Role)'

    def get_employer(self, instance):
        if instance.profile.employer:
            return instance.profile.employer.user.username
        return "-"
    get_employer.short_description = 'صاحب العمل (Vendor)'


# 3. Re-register User
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# 4. Also register UserProfile separately so you can see the staff list


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'role', 'employer', 'phone')
    list_filter = ('role',)
    search_fields = ('user__username', 'phone')
