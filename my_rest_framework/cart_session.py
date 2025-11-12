# my_rest_framework/cart_session.py
from decimal import Decimal
from django.conf import settings
from shop.models import Product

CART_KEY = getattr(settings, "CART_SESSION_ID", "cart")

class CartSession:
    """
    Session-backed cart that stores ONLY JSON-safe data:
      { "<product_id>": {"quantity": int, "price": "9.99"} }
    """
    def __init__(self, request):
        self.request = request
        self.session = request.session
        cart = self.session.get(CART_KEY)
        if not isinstance(cart, dict):
            cart = {}
            self.session[CART_KEY] = cart
        self.cart = cart

    # ---- helpers (do NOT store Decimals back into self.cart) ----
    def _as_decimal(self, price_str: str) -> Decimal:
        try:
            return Decimal(price_str)
        except Exception:
            return Decimal("0")

    # ---- core ops ----
    def add(self, product: Product, quantity: int = 1, override_quantity: bool = False):
        pid = str(product.id)
        if pid not in self.cart:
            # price as STRING so it’s JSON-serializable in session
            self.cart[pid] = {"quantity": 0, "price": str(product.price)}
        if override_quantity:
            self.cart[pid]["quantity"] = int(max(1, quantity))
        else:
            self.cart[pid]["quantity"] = int(self.cart[pid]["quantity"]) + int(max(1, quantity))
        self._save()

    def remove(self, product_id: int):
        pid = str(product_id)
        if pid in self.cart:
            del self.cart[pid]
            self._save()

    def clear(self):
        self.session[CART_KEY] = {}
        self.cart = self.session[CART_KEY]
        self._save()

    def set_quantity(self, product_id: int, quantity: int):
        pid = str(product_id)
        if pid in self.cart:
            self.cart[pid]["quantity"] = int(max(1, quantity))
            self._save()

    # ---- reading/summary (safe to use Decimal in locals) ----
    def items(self):
        """Return a list of line items with model fields (not stored in session)."""
        pids = list(self.cart.keys())
        products = {str(p.id): p for p in Product.objects.filter(id__in=pids)}
        rows = []
        for pid, row in self.cart.items():
            p = products.get(pid)
            if not p:
                continue
            qty = int(row.get("quantity", 1))
            unit = self._as_decimal(row.get("price", "0"))
            rows.append({
                "product_id": int(pid),
                "name": p.name,
                "product_image": getattr(p, "image", None) or "",
                "price": str(unit),                              # string in API payload
                "quantity": qty,
                "line_total": str(unit * Decimal(qty)),          # string in API payload
            })
        return rows

    def totals(self):
        items = self.items()
        subtotal = sum(Decimal(i["line_total"]) for i in items) if items else Decimal("0")
        return {
            "subtotal": str(subtotal),
            "discount": "0",           # plug in coupon logic later if needed
            "total": str(subtotal),
        }

    def snapshot(self):
        """Shape used by API responses."""
        data = self.totals()
        data["items"] = self.items()
        return data

    def _save(self):
        # Mark session dirty; Django JSON-encodes it (now safe)
        self.session.modified = True
