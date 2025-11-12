# customers/serializers.py
from rest_framework import serializers
from .models import Customer

class CustomerSer(serializers.ModelSerializer):
    last_order_at = serializers.DateTimeField(read_only=True)
    total_orders = serializers.IntegerField(read_only=True)

    class Meta:
        model = Customer
        fields = ("id","name","customer_type","email","phone","address","city","state","postal_code","country","lat","lng","created","last_order_at","total_orders")
        read_only_fields = ("id","created","last_order_at","total_orders")
