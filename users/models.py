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
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES,
                              null=True, blank=True, verbose_name="الجنس (Gender)")
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
