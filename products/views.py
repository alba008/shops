# products/views.py
from rest_framework import viewsets, permissions
from .models import Product
from .serializers import ProductSer

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().order_by("name")
    serializer_class = ProductSer
    permission_classes = [permissions.IsAuthenticated]
