# orders/serializers.py
from __future__ import annotations

from decimal import Decimal
from typing import Any
from rest_framework import serializers
from .models import Order, OrderItem

try:
    from shop.utils.media import ensure_media_url
except Exception:
    ensure_media_url = None


# ----------------------- Utils -----------------------
def _dollars(v) -> str:
    """
    Safely cast Decimal/number to normalized string dollars (two decimals).
    """
    try:
        if isinstance(v, Decimal):
            return f"{v:.2f}"
        return f"{Decimal(v or 0):.2f}"
    except Exception:
        return "0.00"


def _first_attr(obj: Any, *names, default=None, fallback_obj: Any = None):
    """
    Return the first present, non-empty attribute from a list of candidates.
    If not found on `obj`, also try `fallback_obj` (e.g., the Order instance).
    """
    for n in names:
        if hasattr(obj, n):
            val = getattr(obj, n)
            if val not in (None, "", []):
                return val
    if fallback_obj is not None:
        for n in names:
            if hasattr(fallback_obj, n):
                val = getattr(fallback_obj, n)
                if val not in (None, "", []):
                    return val
    return default


# ----------------------- Order Item Serializer -----------------------
class OrderItemOut(serializers.ModelSerializer):
    product_id = serializers.SerializerMethodField()
    product_name = serializers.SerializerMethodField()
    product_image = serializers.SerializerMethodField()
    line_total = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = (
            "id",
            "price",
            "quantity",
            "line_total",
            "product_id",
            "product_name",
            "product_image",
        )
        read_only_fields = fields

    def _get_product_obj(self, obj):
        for attr in ("product", "item", "variant"):
            if hasattr(obj, attr) and getattr(obj, attr) is not None:
                return getattr(obj, attr)
        return None

    def get_product_id(self, obj):
        prod = self._get_product_obj(obj)
        return getattr(prod, "pk", None) if prod is not None else None

    def get_product_name(self, obj):
        prod = self._get_product_obj(obj)
        if prod is None:
            return None
        for attr in ("name", "title", "product_name"):
            val = getattr(prod, attr, None)
            if val:
                return val
        try:
            return str(prod)
        except Exception:
            return None

    def get_product_image(self, obj):
        prod = self._get_product_obj(obj)
        if prod is None:
            return None
        for attr in ("image", "thumbnail", "main_image"):
            try:
                img = getattr(prod, attr, None)
                url = getattr(img, "url", None)
                if url:
                    return ensure_media_url(url) if ensure_media_url else url
            except Exception:
                continue
        return None

    def get_line_total(self, obj):
        try:
            price = Decimal(obj.price) if obj.price is not None else Decimal("0")
            qty = obj.quantity or 0
            return _dollars(price * qty)
        except Exception:
            return "0.00"


# ----------------------- Order Serializer (authoritative totals) -----------------------
class OrderOut(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()
    shipping = serializers.SerializerMethodField()

    # Server-persisted monetary fields (do NOT recompute on client)
    subtotal_amount = serializers.SerializerMethodField()
    discount_amount = serializers.SerializerMethodField()
    shipping_amount = serializers.SerializerMethodField()
    tax_rate        = serializers.SerializerMethodField()
    tax_amount      = serializers.SerializerMethodField()
    total_amount    = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = (
            "id",
            "first_name",
            "last_name",
            "email",
            "paid",
            "created",

            # authoritative amounts (strings)
            "subtotal_amount",
            "discount_amount",
            "shipping_amount",
            "tax_rate",
            "tax_amount",
            "total_amount",

            "items",
            "shipping",
        )
        read_only_fields = fields

    # ---- items ----
    def _order_items_qs(self, order):
        related = getattr(order, "items", None)
        return related.all() if related is not None else order.orderitem_set.all()

    def get_items(self, obj):
        return OrderItemOut(self._order_items_qs(obj), many=True).data

    # ---- monetary passthrough (no recompute) ----
    def get_subtotal_amount(self, obj): return _dollars(getattr(obj, "subtotal_amount", 0))
    def get_discount_amount(self, obj): return _dollars(getattr(obj, "discount_amount", 0))
    def get_shipping_amount(self, obj): return _dollars(getattr(obj, "shipping_amount", 0))
    def get_tax_amount(self, obj):      return _dollars(getattr(obj, "tax_amount", 0))
    def get_total_amount(self, obj):    return _dollars(getattr(obj, "total_amount", 0))

    def get_tax_rate(self, obj):
        """
        Return tax rate as a normalized string (e.g., '0.08875').
        Keep as rate, not percent. Client can format as needed.
        """
        try:
            v = getattr(obj, "tax_rate", Decimal("0"))
            if isinstance(v, Decimal):
                return f"{v.normalize()}"
            return str(Decimal(v or 0).normalize())
        except Exception:
            return "0"

    # ---- shipping block ----
    def _get_shipping_obj(self, order):
        for rel in ("shipping_address", "shipping", "address", "ship_to"):
            if hasattr(order, rel) and getattr(order, rel) is not None:
                return getattr(order, rel)
        return order  # fall back to fields on Order itself

    def get_shipping(self, obj):
        ship = self._get_shipping_obj(obj)

        first_name = _first_attr(ship, "first_name", "given_name", "contact_first_name",
                                 "shipping_first_name", "ship_first_name", fallback_obj=obj)
        last_name  = _first_attr(ship, "last_name", "family_name", "contact_last_name",
                                 "shipping_last_name", "ship_last_name", fallback_obj=obj)
        company    = _first_attr(ship, "company", "organization", "shipping_company", "ship_company",
                                 fallback_obj=obj)

        # include plain "address" and fall back to Order.address if needed
        address1   = _first_attr(ship, "address1", "line1", "street1", "street",
                                 "address_line1", "address_line_1", "address",
                                 fallback_obj=obj)
        address2   = _first_attr(ship, "address2", "line2", "street2",
                                 "address_line2", "address_line_2",
                                 fallback_obj=obj)

        city       = _first_attr(ship, "city", "locality", "town", "shipping_city", "ship_city",
                                 fallback_obj=obj)
        state      = _first_attr(ship, "state", "region", "province", "county",
                                 "shipping_state", "ship_state",
                                 fallback_obj=obj)
        postal     = _first_attr(ship, "postal_code", "zip", "postcode",
                                 "shipping_postal_code", "shipping_zip", "ship_postal_code", "ship_zip",
                                 fallback_obj=obj)
        country    = _first_attr(ship, "country", "country_code", "shipping_country", "ship_country",
                                 fallback_obj=obj)
        phone      = _first_attr(ship, "phone", "telephone", "mobile",
                                 "shipping_phone", "ship_phone",
                                 fallback_obj=obj)
        email      = _first_attr(ship, "email", "contact_email", "shipping_email", "ship_email",
                                 fallback_obj=obj)

        payload = {
            "first_name": first_name,
            "last_name": last_name,
            "company": company,
            "address1": address1,
            "address2": address2,
            "city": city,
            "state": state,
            "postal_code": postal,
            "country": country,
            "phone": phone,
            "email": email,
        }
        if not any(payload.values()):
            return None

        parts = [p for p in [
            f"{first_name or ''} {last_name or ''}".strip() or None,
            company,
            address1,
            address2,
            f"{city or ''}{', ' + state if state else ''} {postal or ''}".strip(),
            country
        ] if p]
        payload["display"] = " · ".join(parts) if parts else None
        return payload
