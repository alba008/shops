# myshop/middleware/session_touch.py
from django.utils.deprecation import MiddlewareMixin

class SessionTouchMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # If you can compute cart count quickly, set it here.
        # Example if you use a session-based cart:
        try:
            cart = request.session.get("cart", {})
            count = sum(int(v.get("quantity", 0)) for v in cart.values()) if isinstance(cart, dict) else 0
            request.session["cart_count"] = count
        except Exception:
            pass
