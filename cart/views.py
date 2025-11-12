# cart/views.py
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from coupons.forms import CouponApplyForm
from shop.models import Product
from shop.recommender import Recommender

from .cart import Cart
from .forms import CartAddProductForm


@require_POST
def cart_add(request, product_id):
    """
    Add a product to the cart or update its quantity.
    """
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    form = CartAddProductForm(request.POST)
    if form.is_valid():
        cd = form.cleaned_data
        cart.add(
            product=product,
            quantity=cd["quantity"],
            override_quantity=cd["override"],
        )
    return redirect("cart:cart_detail")


@require_POST
def cart_remove(request, product_id):
    """
    Remove a product from the cart.
    """
    cart = Cart(request)
    product = get_object_or_404(Product, id=product_id)
    cart.remove(product)
    return redirect("cart:cart_detail")


def cart_detail(request):
    """
    Render the cart page (template-based flow).
    """
    cart = Cart(request)
    steps = ["Cart", "Shipping", "Payment", "Review"]

    # attach inline quantity form for each line
    for item in cart:
        item["update_quantity_form"] = CartAddProductForm(
            initial={"quantity": item["quantity"], "override": True}
        )

    coupon_apply_form = CouponApplyForm()

    # simple recommender (as in your original)
    r = Recommender()
    cart_products = [item["product"] for item in cart]
    recommended_products = (
        r.suggest_products_for(cart_products, max_results=4) if cart_products else []
    )

    return render(
        request,
        "cart/detail.html",
        {
            "cart": cart,
            "coupon_apply_form": coupon_apply_form,
            "recommended_products": recommended_products,
            "steps": steps,
            "current_step": 1,
        },
    )


# ------------ API helper: hard-clear the server-side cart ------------
@csrf_exempt
@require_POST
def empty_cart(request):
    """
    Hard clear the cart/coupon in the user session.
    Useful for post-checkout (Thank You page) to ensure no stale session data remains.
    Returns JSON: { "ok": true }
    """
    try:
        # Clear the configured cart session key and common aliases
        cart_keys = {
            getattr(settings, "CART_SESSION_ID", "cart"),
            "cart",
            "basket",
            "session_cart",
            "myshop_cart",
        }
        for key in cart_keys:
            request.session.pop(key, None)

        # Clear any coupon session keys you might set
        for key in ("coupon_id", "coupon", "cart_coupon"):
            request.session.pop(key, None)

        # Also invoke the Cart helper for good measure
        try:
            Cart(request).clear()
        except Exception:
            pass

        request.session.modified = True
        return JsonResponse({"ok": True})
    except Exception as e:
        return JsonResponse({"ok": False, "detail": str(e)}, status=500)
