from rest_framework import serializers
from .models import Order
from .serializers import OrderOut, OrderItemOut

class OrderListSer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ("id", "first_name", "last_name", "email", "paid", "created")
        read_only_fields = fields

class OrderDetailAdminSer(OrderOut):
    items = serializers.SerializerMethodField()

    class Meta(OrderOut.Meta):
        fields = OrderOut.Meta.fields

    def get_items(self, obj):
        related = getattr(obj, "items", None)
        qs = related.all() if related is not None else obj.orderitem_set.all()
        return OrderItemOut(qs, many=True).data
