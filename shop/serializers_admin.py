# shop/serializers_admin.py
from rest_framework import serializers
from .models import Product


class AdminProductSer(serializers.ModelSerializer):
    category_name = serializers.CharField(source="category.name", read_only=True)

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "slug",
            "category",
            "category_name",
            "price",
            "stock",
            "available",
            "brand",
        ]
