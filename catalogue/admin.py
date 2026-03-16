from django.contrib import admin
from .models import Category, Item, Service, ItemServicePrice
from django.utils.html import format_html


class ItemServiceInline(admin.TabularInline):
    model = ItemServicePrice
    # Added 'percentage' so it shows up as a column next to 'price'
    fields = ('service', 'price', 'percentage')
    extra = 1


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name_en', 'name_ar')


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name_en', 'name_ar')


@admin.register(Item)
class ItemAdmin(admin.ModelAdmin):
    list_display = ('thumbnail', 'name_en', 'name_ar', 'category')
    list_filter = ('category',)
    inlines = [ItemServiceInline]

    def thumbnail(self, obj):
        if obj.image:
            return format_html(
                '<img src="{}" style="width: 50px; height: 50px; border-radius: 5px; object-fit: cover;" />',
                obj.image.url
            )
        return "No Image"

    thumbnail.short_description = 'Preview'


@admin.register(ItemServicePrice)
class ItemServicePriceAdmin(admin.ModelAdmin):
    """
    Optional: Registering this separately allows you to filter 
    all items by specific price or percentage ranges.
    """
    list_display = ('item', 'service', 'price', 'percentage')
    list_filter = ('service', 'item__category')
    search_fields = ('item__name_en', 'service__name_en')
