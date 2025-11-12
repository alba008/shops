# customers/models.py
from django.db import models

class Customer(models.Model):
    RETAIL = "RETAIL"
    WHOLESALE = "WHOLESALE"
    TYPES = [(RETAIL,"Retail"),(WHOLESALE,"Wholesale")]

    name = models.CharField(max_length=200)
    customer_type = models.CharField(max_length=12, choices=TYPES, default=RETAIL)
    email = models.EmailField(blank=True, null=True)
    phone = models.CharField(max_length=64, blank=True, null=True)
    address = models.CharField(max_length=250, blank=True, null=True)
    city = models.CharField(max_length=120, blank=True, null=True)
    state = models.CharField(max_length=120, blank=True, null=True)
    postal_code = models.CharField(max_length=32, blank=True, null=True)
    country = models.CharField(max_length=64, blank=True, null=True)
    lat = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    lng = models.DecimalField(max_digits=9, decimal_places=6, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)

    def __str__(self): return self.name
