# myshop/cart/cart.py
from decimal import Decimal
from django.conf import settings
from coupons.models import Coupon
from django.apps import apps

def _cart_key() -> str:
    return getattr(settings, "CART_SESSION_ID", "cart")

class Cart:
    def __init__(self, request):
        self.session = request.session
        key = _cart_key()
        cart = self.session.get(key)
        if not cart:
            cart = self.session[key] = {}
        self.cart = cart
        self.coupon_id = self.session.get("coupon_id")

    def add(self, product, quantity=1, override_quantity=False):
        product_id = str(product.id)
        if product_id not in self.cart:
            self.cart[product_id] = {
                "quantity": 0,
                "price": str(product.price),  # keep as str in session
            }
        if override_quantity:
            self.cart[product_id]["quantity"] = int(quantity)
        else:
            self.cart[product_id]["quantity"] += int(quantity)
        self.save()

    def save(self):
        self.session[_cart_key()] = _to_jsonable(self.cart)
        self.session.modified = True

    def remove(self, product):
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def __iter__(self):
        """Yield computed, non-session objects without mutating session data."""
        Product = get_product_model()
        product_ids = list(self.cart.keys())

        products_by_id = {str(p.id): p for p in Product.objects.filter(id__in=product_ids)}

        for pid, data in self.cart.items():
            product = products_by_id.get(pid)
            if not product:
                continue
            price = Decimal(data["price"])
            qty = int(data["quantity"])
            yield {
                "product": product,
                "price": price,
                "quantity": qty,
                "total_price": price * qty,
            }

    def __len__(self):
        return sum(int(item["quantity"]) for item in self.cart.values())

    def get_total_price(self):
        return sum(Decimal(item["price"]) * int(item["quantity"]) for item in self.cart.values())

    @property
    def coupon(self):
        if self.coupon_id:
            try:
                return Coupon.objects.get(id=self.coupon_id)
            except Coupon.DoesNotExist:
                return None
        return None

    def get_discount(self):
        if self.coupon:
            return (self.coupon.discount / Decimal(100)) * self.get_total_price()
        return Decimal(0)

    def get_total_price_after_discount(self):
        return self.get_total_price() - self.get_discount()

    def clear(self):
        key = _cart_key()
        if key in self.session:
            del self.session[key]
        self.session.modified = True


def get_product_model():
    return apps.get_model("shop", "Product")

def get_coupon_model():
    return apps.get_model("coupons", "Coupon")

def _to_jsonable(x):
    if isinstance(x, Decimal):
        return str(x)
    if isinstance(x, dict):
        return {k: _to_jsonable(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [_to_jsonable(v) for v in x]
    return x
