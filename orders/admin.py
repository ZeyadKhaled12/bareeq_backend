from django.contrib import admin
from django.utils.html import format_html
from .models import Order, OrderItem, SelectedService,  Invoice
from catalogue.models import ItemServicePrice


class SelectedServiceInline(admin.TabularInline):
    model = SelectedService
    extra = 1
    verbose_name = "الخدمة المطلوبة"
    verbose_name_plural = "الخدمات المطلوبة لهذه القطعة"

    # THIS IS THE MAGIC: It filters services based on the Item type
    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if db_field.name == "item_service_price":
            # Look for the ID of the OrderItem in the URL
            resolved = request.resolver_match
            if resolved and 'object_id' in resolved.kwargs:
                try:
                    order_item = OrderItem.objects.get(
                        pk=resolved.kwargs['object_id'])
                    # Only show prices/services linked to this specific item type
                    kwargs["queryset"] = ItemServicePrice.objects.filter(
                        item=order_item.item_type)
                except OrderItem.DoesNotExist:
                    pass
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 1
    fields = ('item_type', 'tag_code')  # Keep it simple in the main order view
    show_change_link = True  # This adds a small pencil icon to go to the Photo/Service page
    verbose_name = "قطعة ملابس"
    verbose_name_plural = "قطع الملابس في هذا الطلب"


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    # What you see in the main list
    list_display = ('invoice_number', 'order', 'total_amount', 'is_paid')

    # These fields should not be editable by hand to prevent accounting errors
    readonly_fields = ('invoice_number', 'subtotal', 'vat_amount',
                       'delivery_charge', 'total_amount', 'issued_at')

    # Only allow staff to check if it's paid
    fields = ('order', 'invoice_number', 'subtotal', 'vat_amount',
              'delivery_charge', 'total_amount', 'is_paid', 'issued_at')


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('barcode', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('barcode',)
    inlines = [OrderItemInline]

    # Optional: Colors for the status
    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        return form


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('tag_code', 'item_type', 'order', 'show_vendor_photo')
    list_filter = ('order__status',)
    inlines = [SelectedServiceInline]

    readonly_fields = ('show_vendor_photo', 'show_finished_photo')

    def show_vendor_photo(self, obj):
        if obj.photo_at_vendor:
            return format_html('<img src="{}" style="width: 80px; height: 80px; border-radius: 5px;" />', obj.photo_at_vendor.url)
        return "No Photo"
    show_vendor_photo.short_description = "صورة الاستلام"

    def show_finished_photo(self, obj):
        if obj.photo_finished:
            return format_html('<img src="{}" style="width: 80px; height: 80px; border-radius: 5px;" />', obj.photo_finished.url)
        return "No Photo"
    show_finished_photo.short_description = "صورة الانتهاء"
