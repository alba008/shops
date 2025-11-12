from rest_framework import serializers
from .models import (
    Category, SubCategory, Product, Color, Size,
    Banner, GalleryImage, ProductImage,  MarketingImage 
)


class CategorySerializer(serializers.ModelSerializer):
    child_categories = serializers.StringRelatedField(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'slug', 'parent', 'child_categories']


class SubCategorySerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()

    class Meta:
        model = SubCategory
        fields = ['id', 'category', 'name', 'slug']


class ColorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Color
        fields = ['id', 'name', 'hex']


class SizeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Size
        fields = ['id', 'label']


class ProductImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = ProductImage
        fields = ["id", "product", "image_url", "alt_text"]

    def get_image_url(self, obj):
        request = self.context.get("request")
        return request.build_absolute_uri(obj.image.url) if request else obj.image.url


class ProductSerializer(serializers.ModelSerializer):
    image_url_resolved = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = ["id", "name", "slug", "image_url_resolved", "price", "available", "rating"]

    def get_image_url_resolved(self, obj):
        request = self.context.get("request")
        # Prefer uploaded file
        if getattr(obj, "image", None):
            try:
                return request.build_absolute_uri(obj.image.url) if request else obj.image.url
            except Exception:
                pass
        # Fallback to URL field (may be bare filename)
        if getattr(obj, "image_url", None):
            return _abs_media(request, obj.image_url)
        return None


class BannerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Banner
        fields = ['id', 'image', 'title', 'description', 'link']

class GalleryImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = GalleryImage
        fields = ["id", "title", "uploaded_at", "image_url"]

    def get_image_url(self, obj):
        request = self.context.get("request")
        return request.build_absolute_uri(obj.image.url) if request else obj.image.url


class MarketingImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = MarketingImage
        fields = "__all__"