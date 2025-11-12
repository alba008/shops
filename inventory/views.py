# inventory/views.py
from django.db.models import Sum, F
from rest_framework import viewsets, permissions, mixins
from rest_framework.decorators import action
from rest_framework.response import Response
from .models import StockLedger
from .serializers import StockLedgerSer, InventorySnapshotRowSer
from products.models import Product

class StockLedgerViewSet(mixins.ListModelMixin,
                         mixins.CreateModelMixin,
                         mixins.DestroyModelMixin,
                         viewsets.GenericViewSet):
    queryset = StockLedger.objects.select_related("product","customer","user")
    serializer_class = StockLedgerSer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=False, methods=["get"])
    def snapshot(self, request):
        # on-hand = sum(delta) per product where track_stock=True
        sums = (StockLedger.objects
                .values("product_id")
                .annotate(on_hand=Sum("delta")))
        on_by_id = {row["product_id"]: row["on_hand"] or 0 for row in sums}
        rows = []
        for p in Product.objects.filter(track_stock=True):
            rows.append({
                "product_id": p.id,
                "name": p.name,
                "sku": p.sku,
                "on_hand": int(on_by_id.get(p.id, 0)),
            })
        ser = InventorySnapshotRowSer(rows, many=True)
        return Response(ser.data)
