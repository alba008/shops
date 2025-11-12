# shop/views_admin.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from .models import Product

@api_view(["GET"])
@permission_classes([IsAdminUser])
def low_stock(request):
    limit = int(request.query_params.get("limit", 8))
    threshold = int(request.query_params.get("threshold", 5))
    qs = Product.objects.filter(available=True, stock__lte=threshold).order_by("stock")[:limit]
    return Response([{"id": p.id, "name": p.name, "sku": getattr(p, "sku", None), "stock": p.stock} for p in qs])

@api_view(["GET"])
@permission_classes([IsAdminUser])
def products(request):
    qs = Product.objects.all().order_by("id")
    return Response([{
        "id": p.id, "name": p.name,
        "category_name": getattr(p.category, "name", None),
        "price": p.price, "available": p.available
    } for p in qs])
