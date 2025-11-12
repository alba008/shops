# cart/utils.py
from .models import Cart

def get_or_create_cart(request):
    """
    If authenticated -> user cart
    Else -> session cart (create session key if missing)
    """
    user = getattr(request, "user", None)
    if user and user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=user, checked_out=False)
        return cart

    if not request.session.session_key:
        request.session.create()
    cart, _ = Cart.objects.get_or_create(
        session_key=request.session.session_key, checked_out=False
    )
    return cart
