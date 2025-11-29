# myshop/my_rest_framework/serializers.py

from rest_framework import serializers
from orders.models import Order


class OrderCreateSerializer(serializers.ModelSerializer):
    """
    Serializer for creating an Order from checkout form.
    Only exposes the fields that the frontend actually sends.
    """

    class Meta:
        model = Order
        fields = [
            "first_name",
            "last_name",
            "email",
            "address",
            "postal_code",
            "city",
            "ship_state",
            "ship_country",
            "shipping_method",
        ]
