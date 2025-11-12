# myshop/my_rest_framework/views_session.py
from django.contrib.sessions.models import Session
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from django.views.decorators.http import require_GET


class SessionView(APIView):
    permission_classes = [AllowAny]

   # myshop/my_rest_framework/views_session.py
from django.views.decorators.http import require_GET
from django.utils.timezone import now
from django.http import JsonResponse           # <-- you were missing this
from django.contrib.auth.models import AnonymousUser

try:
    from cart.cart import Cart                 # optional, if you have Cart
except Exception:
    Cart = None

@require_GET
def session_state(request):
    # Ensure the session exists so we can store/read keys
    _ = request.session.session_key
    if _ is None:
        request.session.save()  # force creation

    # Read whatever you’ve been setting elsewhere
    last_order_id = request.session.get("last_order_id")
    order_id      = request.session.get("order_id")  # if you also use this key

    # Optional cart count if your Cart is available
    cart_count = 0
    if Cart is not None:
        try:
            cart = Cart(request)
            cart_count = len(cart)
        except Exception:
            cart_count = 0

    user = request.user if request.user and not isinstance(request.user, AnonymousUser) else None

    return JsonResponse({
        "session_key": request.session.session_key,
        "is_authenticated": bool(user and user.is_authenticated),
        "user": {
            "id": getattr(user, "id", None),
            "email": getattr(user, "email", None),
            "first_name": getattr(user, "first_name", None),
            "last_name": getattr(user, "last_name", None),
        } if user and user.is_authenticated else None,

        # keys your frontend reads:
        "last_order_id": last_order_id or order_id,
        "cart_count": cart_count,

        # helpful for debugging
        "now": now().isoformat(),
    })

class SessionAttachOrderView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        oid = request.data.get("order_id")
        if not oid:
            return Response({"detail": "order_id required"}, status=status.HTTP_400_BAD_REQUEST)
        request.session["last_order_id"] = int(oid)
        request.session.modified = True
        return Response({"ok": True, "last_order_id": oid})

@require_GET
def session_state(request):
    return JsonResponse({
        "session_key": request.session.session_key,
        "is_authenticated": request.user.is_authenticated,
        "user": getattr(request.user, "username", None) if request.user.is_authenticated else None,
        "last_order_id": request.session.get("last_order_id"),
        "cart_count": request.session.get("cart_count", 0),
    })