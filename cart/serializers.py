from rest_framework import serializers
from shop.models import Product


class ProductMiniSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'image']


class CartItemAddSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=1, default=1)

class CartItemUpdateSerializer(serializers.Serializer):
    product_id = serializers.IntegerField(min_value=1)
    quantity = serializers.IntegerField(min_value=0)  # 0 = remove

class CartLineSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField()
    unit_price = serializers.FloatField()
    line_total = serializers.FloatField()

class CartSerializer(serializers.Serializer):
    items = CartLineSerializer(many=True)
    subtotal = serializers.FloatField()

   

class CartLineSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    title = serializers.CharField()
    quantity = serializers.IntegerField()
    price = serializers.CharField()
    total_price = serializers.CharField()

class CartItemSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField()
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2)
