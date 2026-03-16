from django.db import models


class Category(models.Model):
    name_en = models.CharField(
        max_length=100, unique=True, verbose_name="Name (EN)")
    name_ar = models.CharField(
        max_length=100, unique=True, verbose_name="الاسم (عربي)")

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        # This shows both names in the Admin dropdowns
        return f"{self.name_en} / {self.name_ar}"


class Service(models.Model):
    name_en = models.CharField(
        max_length=100, verbose_name="Service Name (EN)")
    name_ar = models.CharField(
        max_length=100, verbose_name="اسم الخدمة (عربي)")

    class Meta:
        verbose_name = "Service"
        verbose_name_plural = "Services"

    def __str__(self):
        return f"{self.name_en} / {self.name_ar}"


# ... Category and Service models remain the same ...


class Item(models.Model):
    name_en = models.CharField(max_length=100, verbose_name="Item Name (EN)")
    name_ar = models.CharField(
        max_length=100, verbose_name="اسم القطعة (عربي)")
    image = models.ImageField(
        upload_to='items/', null=True, blank=True, verbose_name="Photo / صورة")
    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="items")

    # The ManyToMany relationship points to the updated through model
    services = models.ManyToManyField(Service, through='ItemServicePrice')

    class Meta:
        verbose_name = "Item"
        verbose_name_plural = "Items"

    def __str__(self):
        return f"{self.name_en} ({self.category.name_en})"


class ItemServicePrice(models.Model):
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE)

    # 1. Existing Price Field
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name="Price (EGP)"
    )

    # 2. NEW Percentage Field
    # Using DecimalField (e.g., 15.50 for 15.5%) is more professional than Integer
    percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0.00,
        verbose_name="Percentage (%)"
    )

    class Meta:
        unique_together = ('item', 'service')
        verbose_name = "Price & Percentage Setting"
        verbose_name_plural = "Price & Percentage Settings"

    def __str__(self):
        return f"{self.item.name_en} - {self.service.name_en}: {self.price} EGP ({self.percentage}%)"
