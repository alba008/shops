from rest_framework import serializers
from cart.cart import Cart
from shop.models import Product

DJANGO_BASE = "http://127.0.0.1:8000"  # adjust via settings if needed


def to_abs_media(url: str) -> str:
    """Ensure product image URLs are absolute."""
    if not url:
        return ""
    s = str(url)
    return f"{DJANGO_BASE}{s}" if s.startswith("/media/") else s


# ----------------------
# INPUT SERIALIZERS
# ----------------------
class CartItemInSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    quantity = serializers.IntegerField(min_value=1, required=False)


class CouponInSerializer(serializers.Serializer):
    code = serializers.CharField()


# ----------------------
# OUTPUT SERIALIZERS
# ----------------------
class CartItemOutSerializer(serializers.Serializer):
    product_id = serializers.IntegerField()
    name = serializers.CharField()
    quantity = serializers.IntegerField()
    price = serializers.FloatField()
    line_total = serializers.FloatField()
    product_image = serializers.CharField(allow_blank=True)

    @staticmethod
    def from_cart_item(item) -> dict:
        """Convert a cart item dict into a serialized dict for the API."""
        product = item.get("product")
        img = getattr(product, "image", None) or getattr(product, "image_url", "")
        return {
            "product_id": getattr(product, "id", None),
            "name": getattr(product, "name", f"Product {getattr(product, 'id', '')}"),
            "quantity": item.get("quantity", 0),
            "price": float(item.get("price", 0)),
            "line_total": float(item.get("total_price", 0)),
            "product_image": to_abs_media(str(img)),
        }


class CartOutSerializer(serializers.Serializer):
    items = CartItemOutSerializer(many=True)
    subtotal = serializers.FloatField()
    discount = serializers.FloatField()
    total = serializers.FloatField()
    coupon = serializers.DictField(required=False)

    @staticmethod
    def from_cart(cart: Cart) -> dict:
        """Serialize a Cart object safely for API response."""
        items = [CartItemOutSerializer.from_cart_item(it) for it in cart]
        data = {
            "items": items,
            "subtotal": float(cart.get_total_price()),
            "discount": float(cart.get_discount()),
            "total": float(cart.get_total_price_after_discount()),
        }

        coupon = getattr(cart, "coupon", None)
        if coupon:
            data["coupon"] = {
                "id": getattr(coupon, "id", None),
                "code": getattr(coupon, "code", ""),
                "discount": float(getattr(coupon, "discount", 0)),
            }

        return data
