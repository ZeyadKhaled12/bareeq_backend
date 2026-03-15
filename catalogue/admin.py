from django.contrib import admin
from .models import Category, Item, Service, ItemServicePrice
from django.utils.html import format_html  # Import this for the thumbnail


class ItemServiceInline(admin.TabularInline):
    model = ItemServicePrice
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    # This shows both English and Arabic in the table list
    list_display = ('name_en', 'name_ar')


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name_en', 'name_ar')


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    # Added 'thumbnail' to the list
    list_display = ('thumbnail', 'name_en', 'name_ar', 'category')
    list_filter = ('category',)
    inlines = [ItemServiceInline]

    # This function creates the small preview image
    def thumbnail(self, obj):
        if obj.image:
            return format_html('<img src="{}" style="width: 50px; height: 50px; border-radius: 5px;" />', obj.image.url)
        return "No Image"

    thumbnail.short_description = 'Preview'
