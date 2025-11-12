from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from shop.models import MarketingImage
from .serializers_content import MarketingImageSerializer

class MarketingImageViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = MarketingImage.objects.filter(is_active=True).order_by("ordering", "-id")
    serializer_class = MarketingImageSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter, filters.SearchFilter]
    filterset_fields = ["section", "is_active"]   # <- only model fields here
    ordering_fields = ["ordering", "id", "created"]
    search_fields = ["title", "subtitle"]
