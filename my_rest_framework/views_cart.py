from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from rest_framework.exceptions import ValidationError

from cart.cart import Cart as SessionCart
from shop.models import Product

# ---- Optional coupon model import (handle if app not installed) ----
try:
    from coupons.models import Coupon  # adjust to your app label if different
    COUPONS_ENABLED = True
except Exception:
    COUPONS_ENABLED = False

DJANGO_BASE = "http://10.0.0.47:8000"

def _abs_media(u: str) -> str:
    if not u:
        return "/media/placeholder.png"
    u = str(u)
    return u if u.startswith("http") else f"{DJANGO_BASE}{u if u.startswith('/') else '/' + u}"

def _cart_payload(c: SessionCart) -> dict:
    items = []
    qty_total = 0
    for it in c:
        p = it["product"]
        q = int(it.get("quantity", 0))
        qty_total += q
        items.append({
            "product_id": p.id,
            "name": getattr(p, "name", f"Product {p.id}"),
            "quantity": q,
            "price": str(it["price"]),                 # Decimal -> str
            "line_total": str(it["total_price"]),
            "product_image": _abs_media(getattr(p, "image", "") or getattr(p, "image_url", "")),
            "slug": getattr(p, "slug", ""),
        })
    data = {
        "items": items,
        "subtotal": str(c.get_total_price()),
        "discount": str(c.get_discount()),
        "total": str(c.get_total_price_after_discount()),
        # Use total quantity for badges:
        "count": qty_total,
        "cart_count": qty_total,
    }
    if getattr(c, "coupon", None):
        data["coupon"] = {
            "id": c.coupon.id,
            "code": c.coupon.code,
            "discount": c.coupon.discount,  # %
        }
    return data

class CartView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        return Response(_cart_payload(SessionCart(request)), headers={"Cache-Control":"no-store"})
    def delete(self, request):
        c = SessionCart(request); c.clear(); request.session.modified = True
        return Response(_cart_payload(c), headers={"Cache-Control":"no-store"})

class CartItemView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        c = SessionCart(request)
        pid = request.data.get("product_id"); qty = int(request.data.get("quantity", 1))
        p = Product.objects.get(pk=pid)
        c.add(p, quantity=qty, override_quantity=False)
        request.session.modified = True
        return Response(_cart_payload(c), headers={"Cache-Control":"no-store"})

    def patch(self, request):
        c = SessionCart(request)
        pid = request.data.get("product_id"); qty = int(request.data.get("quantity", 1))
        p = Product.objects.get(pk=pid)
        c.add(p, quantity=qty, override_quantity=True)
        request.session.modified = True
        return Response(_cart_payload(c), headers={"Cache-Control":"no-store"})

    def delete(self, request):
        c = SessionCart(request)
        pid = request.data.get("product_id")
        p = Product.objects.get(pk=pid)
        c.remove(p)
        request.session.modified = True
        return Response(_cart_payload(c), headers={"Cache-Control":"no-store"})

class CartCountView(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        cart = SessionCart(request)
        total_qty = sum(item["quantity"] for item in cart)
        return Response({"count": total_qty, "cart_count": total_qty}, headers={"Cache-Control":"no-store"})

class CartSummary(APIView):
    permission_classes = [permissions.AllowAny]
    def get(self, request):
        c = SessionCart(request)
        return Response({"cart_count": sum(i["quantity"] for i in c)}, headers={"Cache-Control":"no-store"})

class AddToCart(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        # this is just an example; your real add lives in CartItemView.post
        c = SessionCart(request)
        cart_count = sum(i["quantity"] for i in c)
        return Response({"ok": True, "cart_count": cart_count}, status=status.HTTP_200_OK, headers={"Cache-Control":"no-store"})

# -------- NEW: CouponView to match your urls.py import --------
class CouponView(APIView):
    """
    POST { "code": "SAVE10" }  -> apply coupon to this session's cart
    DELETE                     -> remove coupon from this session's cart
    Returns the updated cart payload in both cases.
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        if not COUPONS_ENABLED:
            raise ValidationError("Coupons feature is not enabled/installed.")
        code = (request.data.get("code") or "").strip()
        if not code:
            raise ValidationError({"code": "Coupon code is required."})

        now = timezone.now()
        try:
            coupon = Coupon.objects.get(
                code__iexact=code,
                active=True,
                valid_from__lte=now,
                valid_to__gte=now,
            )
        except Coupon.DoesNotExist:
            raise ValidationError({"code": "Invalid or expired coupon."})

        cart = SessionCart(request)

        # Common patterns: your Cart may expose `apply_coupon(coupon)`
        # or you store coupon_id in session. We support both gracefully.
        if hasattr(cart, "apply_coupon"):
            cart.apply_coupon(coupon)
        else:
            request.session["coupon_id"] = coupon.id
        request.session.modified = True
        return Response(_cart_payload(cart), headers={"Cache-Control": "no-store"})

    def delete(self, request):
        cart = SessionCart(request)
        # Support both patterns again
        if hasattr(cart, "remove_coupon"):
            cart.remove_coupon()
        else:
            request.session.pop("coupon_id", None)
        request.session.modified = True
        return Response(_cart_payload(cart), headers={"Cache-Control": "no-store"})
