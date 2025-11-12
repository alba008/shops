# inventory/serializers.py
from rest_framework import serializers
from .models import StockLedger
from products.models import Product

class StockLedgerSer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    class Meta:
        model = StockLedger
        fields = ("id","product","product_name","delta","reason","ref_type","ref_id","customer","user","note","created")
        read_only_fields = ("id","created")

class InventorySnapshotRowSer(serializers.Serializer):
    product_id = serializers.IntegerField()
    name = serializers.CharField()
    sku = serializers.CharField(allow_null=True)
    on_hand = serializers.IntegerField()
