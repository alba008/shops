from rest_framework import serializers
from shop.models import MarketingImage

class MarketingImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketingImage
        fields = ["id", "title", "subtitle", "image", "section", "cta_text", "cta_link", "ordering", "is_active", "created"]
