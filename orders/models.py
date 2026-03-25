from django.dispatch import receiver
from django.db.models.signals import post_save, post_delete
from django.db import models
from catalogue.models import Item, Service, ItemServicePrice
import uuid
from decimal import Decimal
from django.core.exceptions import ValidationError


class Order(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'قيد الانتظار - لم يتم الاستلام بعد (Pending Pickup)'),
        ('RECEIVED', 'استلام من المندوب (Received)'),
        ('AT_VENDOR', 'في المغسلة (At Vendor)'),
        ('FINISHED', 'جاهز (Finished)'),
        ('RETURNED', 'تم التسليم (Returned)'),
        ('CANCELED', 'ملغي (Canceled)')
    ]

    barcode = models.CharField(
        max_length=20, unique=True, editable=False, verbose_name="الباركود (Barcode)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                              default='PENDING', verbose_name="حالة الطلب (Status)")
    comment = models.TextField(
        null=True, blank=True, verbose_name="ملاحظات (Comment)")

    # Pickup Details
    time_slot = models.ForeignKey(
        'users.TimeSlot', on_delete=models.PROTECT, related_name='pickup_orders', null=True
    )
    pickup_date = models.DateField(null=True, verbose_name="تاريخ الاستلام")

    # Delivery Details
    delivery_time_slot = models.ForeignKey(
        'users.TimeSlot', on_delete=models.SET_NULL, related_name='delivery_orders',
        null=True, blank=True
    )
    delivery_date = models.DateField(
        null=True, blank=True, verbose_name="تاريخ التوصيل")

    picked_services = models.ManyToManyField(
        Service, blank=True, related_name="orders", verbose_name="الخدمات المختارة (Picked Services)"
    )

    # Pricing
    delivery_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name="مصاريف التوصيل")
    total_price = models.DecimalField(
        max_digits=10, decimal_places=2, default=Decimal('0.00'), verbose_name="إجمالي السعر")

    # Relationships
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="تاريخ الطلب (Date)")
    vendor = models.ForeignKey(
        'users.UserProfile', on_delete=models.CASCADE, related_name='vendor_orders',
        limit_choices_to={'role': 'VENDOR'}, verbose_name="المحل (Vendor)", null=True, blank=True
    )
    customer = models.ForeignKey(
        'users.UserProfile', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='customer_orders', limit_choices_to={'role': 'CUSTOMER'}, verbose_name="العميل (Customer)"
    )
    customer_region = models.ForeignKey(
        'lists.Region', on_delete=models.PROTECT, related_name='customer_orders_at_region',
        verbose_name="منطقة العميل", null=True, blank=True
    )
    customer_latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True)
    customer_longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True)
    processed_by = models.ForeignKey(
        'users.UserProfile', on_delete=models.SET_NULL, null=True, blank=True, related_name='processed_orders'
    )

    class Meta:
        verbose_name = "طلب"
        verbose_name_plural = "الطلبات (Orders)"

    def save(self, *args, **kwargs):
        # 1. Ensure barcode is generated BEFORE the first save to prevent null order_key
        if not self.barcode:
            self.barcode = f"ORD-{uuid.uuid4().hex[:6].upper()}"

        super().save(*args, **kwargs)

        # 2. Automatically trigger invoice/price logic if the order is already in the DB
        # (This handles delivery_fee updates)
        if not kwargs.get('raw', False):
            self.recalculate_and_invoice()

    def recalculate_and_invoice(self):
        """
        Subtotal = (Service Prices)
        Total = Subtotal + Delivery
        """
        from decimal import Decimal
        subtotal = Decimal('0.00')

        # 1. Summing the services
        if self.pk:
            for item in self.items.all():
                for selected in item.selected_services.all():
                    subtotal += selected.item_service_price.price

        # 2. Finalizing the math
        vat_amount = Decimal('0.00')
        delivery = self.delivery_fee or Decimal('0.00')
        total = subtotal + delivery

        # 3. Update Order Table
        from .models import Order
        Order.objects.filter(id=self.id).update(total_price=total)

        # 4. Sync Invoice Table
        from .models import Invoice
        Invoice.objects.update_or_create(
            order=self,
            defaults={
                'invoice_number': f"INV-{self.barcode}",
                'subtotal': subtotal.quantize(Decimal('0.01')),
                'vat_amount': vat_amount,
                'delivery_charge': delivery.quantize(Decimal('0.01')),
                'total_amount': total.quantize(Decimal('0.01')),
            }
        )

    def __str__(self):
        return f"{self.barcode} - {self.get_status_display()}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items',
                              on_delete=models.CASCADE, verbose_name="الطلب (Order)")
    item_type = models.ForeignKey(
        Item, on_delete=models.PROTECT, verbose_name="نوع القطعة (Item Type)")
    tag_code = models.CharField(
        max_length=50, unique=True, verbose_name="كود القطعة (Tag Code)")

    photo_at_vendor = models.ImageField(
        upload_to='orders/vendor/', null=True, blank=True, verbose_name="صورة عند المغسلة (Vendor Photo)")
    photo_finished = models.ImageField(
        upload_to='orders/finished/', null=True, blank=True, verbose_name="صورة بعد الانتهاء (Finished Photo)")

    class Meta:
        verbose_name = "قطعة في الطلب"
        verbose_name_plural = "قطع الطلبات (Order Items)"

    def __str__(self):
        return f"{self.item_type.name_ar} ({self.tag_code})"


class SelectedService(models.Model):
    order_item = models.ForeignKey(
        OrderItem, related_name='selected_services', on_delete=models.CASCADE, verbose_name="القطعة")
    item_service_price = models.ForeignKey(
        ItemServicePrice, on_delete=models.PROTECT, verbose_name="الخدمة (Service)")

    class Meta:
        verbose_name = "خدمة مختارة"
        verbose_name_plural = "الخدمات المختارة (Selected Services)"

    def __str__(self):
        return f"{self.item_service_price.service.name_ar} - {self.item_service_price.price} EGP"


class Invoice(models.Model):
    order = models.OneToOneField(
        Order, on_delete=models.CASCADE, related_name='invoice', verbose_name="الطلب (Order)")

    invoice_number = models.CharField(
        max_length=50, unique=True, editable=False, verbose_name="رقم الفاتورة (Invoice #)")

    subtotal = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="المجموع الفرعي (Subtotal)")

    vat_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="ضريبة القيمة المضافة 14% (VAT)")

    delivery_charge = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="مصاريف التوصيل (Delivery Fee)")

    total_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0, verbose_name="الإجمالي النهائي (Total)")

    is_paid = models.BooleanField(
        default=False, verbose_name="تم الدفع؟ (Is Paid?)")

    issued_at = models.DateTimeField(
        auto_now_add=True, verbose_name="تاريخ الإصدار (Issued Date)")

    class Meta:
        verbose_name = "فاتورة"
        verbose_name_plural = "4. الفواتير (Invoices)"

    def __str__(self):
        return f"فاتورة {self.invoice_number}"
