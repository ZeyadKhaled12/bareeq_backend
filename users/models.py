from datetime import time
from django.contrib.auth import get_user_model
from django.db import models
from django.contrib.auth.models import User


from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('VENDOR', 'صاحب محل (Vendor)'),
        ('EMPLOYEE', 'موظف (Employee)'),
        ('CUSTOMER', 'عميل (Customer)'),
    ]

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name='profile')

    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        default='CUSTOMER',
        verbose_name="نوع المستخدم"
    )

    phone = models.CharField(
        max_length=15,
        verbose_name="رقم الهاتف (Phone)",
        null=True,
        blank=True
    )

    gender = models.ForeignKey(
        'lists.Gender',
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        verbose_name="الجنس (Gender)"
    )

    date_of_birth = models.DateField(
        null=True,
        blank=True,
        verbose_name="تاريخ الميلاد (Date of Birth)"
    )

    # Updated Relationship for Employees
    # related_name='employees' allows vendor.profile.employees.all()
    employer = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,  # Corrected from on_api_delete
        null=True,
        blank=True,
        related_name='employees',
        limit_choices_to={'role': 'VENDOR'},
        verbose_name="صاحب العمل (Employer)"
    )

    @property
    def business_profile(self):
        if self.role == 'EMPLOYEE' and self.employer:
            return self.employer
        return self

    class Meta:
        verbose_name = "ملف المستخدم"
        verbose_name_plural = "ملفات المستخدمين"

    def __str__(self):
        return f"{self.user.username} ({self.get_role_display()})"


User = get_user_model()


class TimeSlot(models.Model):
    start = models.TimeField(default=time(9, 0))  # Defaults to 09:00
    end = models.TimeField(default=time(17, 0))   # Defaults to 17:00
    DAYS = [
        ('monday', 'Monday'), ('tuesday', 'Tuesday'), ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'), ('friday', 'Friday'),
        ('saturday', 'Saturday'), ('sunday', 'Sunday'),
    ]
    TYPES = [('receipt', 'Receipt'), ('delivery', 'Delivery')]

    vendor = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='time_slots'  # <--- This MUST be exactly 'time_slots'
    )
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
