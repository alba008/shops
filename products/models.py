# products/models.py
from django.db import models

class Product(models.Model):
    name = models.CharField(max_length=200)
    sku = models.CharField(max_length=64, unique=True, blank=True, null=True)
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    price_retail = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    price_wholesale = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    track_stock = models.BooleanField(default=True)
    # optional: cached stock; we’ll still compute from ledger for truth
    stock_cached = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)

    def __str__(self): return self.name
