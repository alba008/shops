# my_rest_framework/serializers_gallery.py
from rest_framework import serializers
from shop.models import GalleryImage

class GalleryImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = GalleryImage
        fields = ["id", "image", "product", "caption", "ordering"]
