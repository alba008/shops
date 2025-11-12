# my_rest_framework/serializers_products.py
from rest_framework import serializers
from shop.models import Product, Category, SubCategory  # adjust if your model names differ

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]

class SubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = ["id", "name", "slug"]

class ProductSerializer(serializers.ModelSerializer):
    # Show nested category info (read-only). If you don’t want nested, remove this override.
    category = CategorySerializer(read_only=True)

    class Meta:
        model = Product
        # safest while you iterate—includes all fields from Product
        fields = "__all__"
