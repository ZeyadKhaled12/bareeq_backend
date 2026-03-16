from django.db import models

# Create your models here.


class Gender(models.Model):
    title = models.CharField(max_length=50)  # If it's called 'title'
    name_ar = models.CharField(max_length=50, verbose_name="النوع (العربية)")
    name_en = models.CharField(max_length=50, verbose_name="Gender (English)")

    class Meta:
        verbose_name = "نوع"
        verbose_name_plural = "قائمة الأنواع (Genders List)"

    def __str__(self):
        return f"{self.name_ar} / {self.name_en}"
    

# lists/models.py


class Region(models.Model):
    name_en = models.CharField(max_length=100)
    name_ar = models.CharField(max_length=100)

    def __claire__(self):
        return f"{self.name_en} / {self.name_ar}"
