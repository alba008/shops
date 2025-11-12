# inventory/models.py
from django.db import models
from django.conf import settings
from products.models import Product
from customers.models import Customer

class StockLedger(models.Model):
    PRODUCTION = "PRODUCTION"
    SALE = "SALE"
    ADJUSTMENT = "ADJUSTMENT"
    DAMAGED = "DAMAGED"
    RETURNED = "RETURNED"
    REASONS = [(PRODUCTION,PRODUCTION),(SALE,SALE),(ADJUSTMENT,ADJUSTMENT),(DAMAGED,DAMAGED),(RETURNED,RETURNED)]

    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    # positive for in, negative for out
    delta = models.IntegerField()
    reason = models.CharField(max_length=16, choices=REASONS)
    ref_type = models.CharField(max_length=32, blank=True, null=True)  # e.g. "order"
    ref_id = models.CharField(max_length=64, blank=True, null=True)
    customer = models.ForeignKey(Customer, null=True, blank=True, on_delete=models.SET_NULL)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL)
    note = models.CharField(max_length=250, blank=True, null=True)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created"]
