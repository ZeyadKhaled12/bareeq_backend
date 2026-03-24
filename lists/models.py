from django.db import models


class Gender(models.Model):
    title = models.CharField(max_length=50)
    name_ar = models.CharField(max_length=50, verbose_name="النوع (العربية)")
    name_en = models.CharField(max_length=50, verbose_name="Gender (English)")

    class Meta:
        verbose_name = "نوع"
        verbose_name_plural = "قائمة الأنواع (Genders List)"

    def __str__(self):
        return f"{self.name_ar} / {self.name_en}"


class Region(models.Model):
    name_en = models.CharField(max_length=100)
    name_ar = models.CharField(max_length=100)

    class Meta:
        verbose_name = "منطقة"
        verbose_name_plural = "المناطق (Regions)"

    def __str__(self):
        return f"{self.name_en} / {self.name_ar}"
