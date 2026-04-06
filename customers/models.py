from django.db import models

class Customer(models.Model):
    full_name = models.CharField(max_length=255)
    contact_number = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['full_name']

    def __str__(self):
        return self.full_name
