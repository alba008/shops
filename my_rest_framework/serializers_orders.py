# orders/serializers.py
from decimal import Decimal
from rest_framework import serializers
from orders.models import Order, OrderItem
from shop.serializers import ProductSerializer  # keep your existing product serializer


def _num(x):
    try:
        return float(x)
    except Exception:
        return 0.0


# -----------------------------
# Item serializers
# -----------------------------
class OrderItemModelSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ["id", "product", "price", "quantity"]


# -----------------------------
# Order create
# -----------------------------
class OrderCreateSerializer(serializers.ModelSerializer):
    # Optional shipping inputs (frontend can omit; defaults applied)
    shipping_method = serializers.CharField(required=False, allow_blank=True, default="standard")
    ship_state      = serializers.CharField(required=False, allow_blank=True, default="")
    ship_country    = serializers.CharField(required=False, allow_blank=True, default="US")

    class Meta:
        model = Order
        fields = [
            "id",
            "first_name", "last_name", "email",
            "address", "postal_code", "city",
            "shipping_method", "ship_state", "ship_country",
        ]

    def create(self, validated_data):
        order = Order.objects.create(**validated_data)
        # Persist initial totals even if there are no items yet
        update_totals = getattr(order, "update_totals", None)
        if callable(update_totals):
            try:
                order.update_totals(save=True)
            except Exception:
                pass
        return order


# -----------------------------
# Order detail/list (read)
# -----------------------------
class OrderDetailSerializer(serializers.ModelSerializer):
    """
    Returns persisted amounts if columns exist:
      subtotal_amount, discount_amount, shipping_amount, tax_amount, tax_rate, total_amount
    Else falls back to legacy methods (subtotal from lines - discount).
    """
    items = OrderItemModelSerializer(source="items", many=True, read_only=True)

    # amounts (numbers, not strings)
    subtotal = serializers.SerializerMethodField()
    discount = serializers.SerializerMethodField()
    shipping_amount = serializers.SerializerMethodField()
    tax_amount = serializers.SerializerMethodField()
    tax_rate = serializers.SerializerMethodField()
    total = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "first_name", "last_name", "email",
            "address", "postal_code", "city",
            "shipping_method", "ship_state", "ship_country",
            "paid", "created", "updated", "stripe_id", "discount", "coupon",
            # derived/persisted money fields exposed to the frontend:
            "subtotal", "discount", "shipping_amount", "tax_amount", "tax_rate", "total",
            "items",
        ]

    # --- helpers ---
    def _has_attr(self, obj, name):
        return hasattr(obj, name) and getattr(obj, name) is not None

    def get_subtotal(self, obj):
        if self._has_attr(obj, "subtotal_amount"):
            return _num(obj.subtotal_amount)
        if hasattr(obj, "get_total_cost_before_discount"):
            return _num(obj.get_total_cost_before_discount())
        # fallback: sum lines
        return _num(sum((it.get_cost() for it in obj.items.all()), Decimal("0.00")))

    def get_discount(self, obj):
        if self._has_attr(obj, "discount_amount"):
            return _num(obj.discount_amount)
        if hasattr(obj, "get_discount"):
            return _num(obj.get_discount())
        # legacy percent on subtotal
        try:
            subtotal = Decimal(self.get_subtotal(obj))
            pct = Decimal(getattr(obj, "discount", 0) or 0) / Decimal(100)
            return _num((subtotal * pct).quantize(Decimal("0.01")))
        except Exception:
            return 0.0

    def get_shipping_amount(self, obj):
        if self._has_attr(obj, "shipping_amount"):
            return _num(obj.shipping_amount)
        # if not persisted, treat as 0 for compatibility
        return 0.0

    def get_tax_amount(self, obj):
        if self._has_attr(obj, "tax_amount"):
            return _num(obj.tax_amount)
        return 0.0

    def get_tax_rate(self, obj):
        if self._has_attr(obj, "tax_rate"):
            return float(obj.tax_rate)  # e.g. 0.08875
        return 0.0

    def get_total(self, obj):
        # Prefer persisted total if present
        if self._has_attr(obj, "total_amount"):
            return _num(obj.total_amount)

        # Legacy: subtotal - discount (+ optional shipping/tax if present)
        subtotal = Decimal(self.get_subtotal(obj))
        discount = Decimal(self.get_discount(obj))
        shipping = Decimal(self.get_shipping_amount(obj))
        tax = Decimal(self.get_tax_amount(obj))
        try:
            return _num((subtotal - discount + shipping + tax).quantize(Decimal("0.01")))
        except Exception:
            # Very old path: legacy total without shipping/tax
            if hasattr(obj, "get_total_cost"):
                return _num(obj.get_total_cost())
            return _num(subtotal - discount)


class OrderListSerializer(serializers.ModelSerializer):
    total = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ["id", "created", "paid", "total"]

    def get_total(self, obj):
        # match the detail serializer's notion of total
        if hasattr(obj, "total_amount") and obj.total_amount is not None:
            return _num(obj.total_amount)
        if hasattr(obj, "get_total_cost"):
            return _num(obj.get_total_cost())
        subtotal = Decimal(getattr(obj, "get_total_cost_before_discount", lambda: 0)())
        discount = Decimal(getattr(obj, "get_discount", lambda: 0)())
        try:
            return _num((subtotal - discount).quantize(Decimal("0.01")))
        except Exception:
            return _num(subtotal - discount)
