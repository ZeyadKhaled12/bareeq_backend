from django.contrib.auth import get_user_model
from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('VENDOR', 'صاحب محل (Vendor)'),
        ('EMPLOYEE', 'موظف (Employee)'),
        ('CUSTOMER', 'عميل (Customer)'),
    ]

    GENDER_CHOICES = [
        ('MALE', 'ذكر (Male)'),
        ('FEMALE', 'أنثى (Female)'),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile')
    role = models.CharField(max_length=10, choices=ROLE_CHOICES,
                            default='CUSTOMER', verbose_name="نوع المستخدم")

    # The 4 fields you requested:
    phone = models.CharField(max_length=15, verbose_name="رقم الهاتف (Phone)")
    # Note: User model already has email, but we can display it here too
  # Change this line:
    gender = models.ForeignKey(
        'lists.Gender',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="الجنس (Gender)"
    )
    date_of_birth = models.DateField(
        null=True, blank=True, verbose_name="تاريخ الميلاد (Date of Birth)")

    # Relationship for Employees
    employer = models.ForeignKey(
        'self', on_delete=models.SET_NULL, null=True, blank=True,
        limit_choices_to={'role': 'VENDOR'}, verbose_name="صاحب العمل"
    )

    class Meta:
        verbose_name = "ملف المستخدم"
        verbose_name_plural = "ملفات المستخدمين"

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


User = get_user_model()


class TimeSlot(models.Model):
    DAYS = [
        ('monday', 'Monday'), ('tuesday', 'Tuesday'), ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'), ('friday', 'Friday'),
        ('saturday', 'Saturday'), ('sunday', 'Sunday'),
    ]
    TYPES = [('receipt', 'Receipt'), ('delivery', 'Delivery')]

    vendor = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='time_slots')
    day = models.CharField(max_length=10, choices=DAYS)
    slot_type = models.CharField(max_length=10, choices=TYPES)

    # Now stores a single range like "09:00-11:00"
    slot = models.CharField(max_length=50)

    is_free = models.BooleanField(default=False)
    unlimit_orders = models.BooleanField(default=False)
    limit_orders = models.PositiveIntegerField(default=0)
    is_close = models.BooleanField(default=False)

    class Meta:
        # Added 'slot' to ordering so times appear in order (e.g., 09:00 before 11:00)
        ordering = ['day', 'slot_type', 'slot']
