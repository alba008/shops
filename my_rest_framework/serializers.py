# myshop/my_rest_framework/serializers.py
from rest_framework import serializers

class OrderCreateSerializer(serializers.Serializer):
    first_name   = serializers.CharField(max_length=50)
    last_name    = serializers.CharField(max_length=50)
    email        = serializers.EmailField()
    address      = serializers.CharField(max_length=250)
    postal_code  = serializers.CharField(max_length=20)
    city         = serializers.CharField(max_length=100)
