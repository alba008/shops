from rest_framework import serializers
from shop.models import Product


class ProductCardSerializer(serializers.ModelSerializer):
 class Meta:
  model = Product
fields = ["id", "name", "price", "image"] # adjust to your fields