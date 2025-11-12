from rest_framework import serializers

class CheckoutInitResponseSerializer(serializers.Serializer):
    client_secret = serializers.CharField()
    amount = serializers.IntegerField()
    currency = serializers.CharField()
