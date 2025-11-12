from rest_framework import serializers
from shop.models import Product, ProductImage, GalleryImage
import django_filters


class ProductSerializer(serializers.ModelSerializer):
    image_url_resolved = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "name", "slug", "image_url_resolved", "price", "rating"]

    def get_image_url_resolved(self, obj):
        request = self.context.get("request")
        if getattr(obj, "image", None):
            try:
                url = obj.image.url
                return request.build_absolute_uri(url) if request else url
            except:
                pass
        if getattr(obj, "image_url", None):
            return obj.image_url
        return None

class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "product", "image_url", "alt_text"]

    def get_image_url(self, obj):
        request = self.context.get("request")
        url = obj.image.url
        return request.build_absolute_uri(url) if request else url

class GalleryImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = GalleryImage
        fields = ["id", "title", "uploaded_at", "image_url"]

    def get_image_url(self, obj):
        request = self.context.get("request")
        url = obj.image.url
        return request.build_absolute_uri(url) if request else url

class ProductImageFilter(django_filters.FilterSet):
    class Meta:
        model = ProductImage
        fields = {"product": ["exact"], "id": ["exact", "in"]}

class GalleryImageFilter(django_filters.FilterSet):
    class Meta:
        model = GalleryImage
        fields = {"id": ["exact", "in"]}  # ← no "product"