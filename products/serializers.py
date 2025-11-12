# products/serializers.py
from rest_framework import serializers
from .models import Product

class ProductSer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ("id","name","sku","image","price_retail","price_wholesale","track_stock","stock_cached","is_active")
        read_only_fields = ("id","stock_cached")
