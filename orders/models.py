from django.db import models
from catalogue.models import Item, Service, ItemServicePrice
import uuid
from decimal import Decimal  # <--- MUST ADD THIS FOR MATH


from django.db import models
from catalogue.models import Item, Service, ItemServicePrice
import uuid
from decimal import Decimal


class Order(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'قيد الانتظار - لم يتم الاستلام بعد (Pending Pickup)'),
        ('RECEIVED', 'استلام من المندوب (Received)'),
        ('AT_VENDOR', 'في المغسلة (At Vendor)'),
        ('FINISHED', 'جاهز (Finished)'),
        ('RETURNED', 'تم التسليم (Returned)'),
    ]

    barcode = models.CharField(
        max_length=20, unique=True, editable=False, verbose_name="الباركود (Barcode)")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                              default='PENDING', verbose_name="حالة الطلب (Status)")

    # 1. NEW FIELD: Comment
    comment = models.TextField(
        null=True, blank=True, verbose_name="ملاحظات (Comment)")

    delivery_fee = models.DecimalField(
        max_digits=10, decimal_places=2, default=20.00, verbose_name="مصاريف التوصيل")
    created_at = models.DateTimeField(
        auto_now_add=True, verbose_name="تاريخ الطلب (Date)")

    # Vendor and Customer relationships
    vendor = models.ForeignKey('users.UserProfile', on_delete=models.CASCADE, related_name='vendor_orders', limit_choices_to={
                               'role': 'VENDOR'}, verbose_name="المحل (Vendor)", null=True, blank=True)
    customer = models.ForeignKey('users.UserProfile', on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='customer_orders', limit_choices_to={'role': 'CUSTOMER'}, verbose_name="العميل (Customer)")

    class Meta:
        verbose_name = "طلب"
        verbose_name_plural = "الطلبات (Orders)"

    def calculate_totals(self):
        """ Calculates math including the new percentage logic """
        subtotal = Decimal('0.00')

        # 2. UPDATED LOGIC: Calculating Picked Services
        for item in self.items.all():
            for selected in item.selected_services.all():
                price_obj = selected.item_service_price
                # Add base price
                subtotal += price_obj.price

                # If there is a percentage (e.g. for special handling), add it to subtotal
                if price_obj.percentage > 0:
                    percentage_amount = price_obj.price * \
                        (price_obj.percentage / Decimal('100.00'))
                    subtotal += percentage_amount

        vat_amount = subtotal * Decimal('0.14')  # 14% VAT
        total_amount = subtotal + vat_amount + self.delivery_fee

        return {
            'subtotal': subtotal.quantize(Decimal('0.01')),
            'vat_amount': vat_amount.quantize(Decimal('0.01')),
            'total': total_amount.quantize(Decimal('0.01'))
        }

    def generate_invoice(self):
        calc = self.calculate_totals()
        inv, created = Invoice.objects.update_or_create(
            order=self,
            defaults={
                'invoice_number': f"INV-{self.barcode}",
                'subtotal': calc['subtotal'],
                'vat_amount': calc['vat_amount'],
                'delivery_charge': self.delivery_fee,
                'total_amount': calc['total']
            }
        )
        return inv

    def save(self, *args, **kwargs):
        if not self.barcode:
            self.barcode = f"ORD-{uuid.uuid4().hex[:6].upper()}"
        super().save(*args, **kwargs)
        if self.status == 'FINISHED':
            self.generate_invoice()

    def __str__(self):
        return f"{self.barcode} - {self.get_status_display()}"
    
    # ... previous fields ...
    vendor = models.ForeignKey(
        'users.UserProfile',
        on_delete=models.CASCADE,
        related_name='vendor_orders',
        limit_choices_to={'role': 'VENDOR'},
        verbose_name="المحل (Vendor)",
        null=True,  # <--- Add this
        blank=True  # <--- Add this
    )
    customer = models.ForeignKey(
        'users.UserProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='customer_orders',
        limit_choices_to={'role': 'CUSTOMER'},
        verbose_name="العميل (Customer)"
    )


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

    # Financial Snapshots with Bilingual Labels
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
