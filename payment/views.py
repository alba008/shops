# payment/views.py
from decimal import Decimal, ROUND_HALF_UP

import stripe
from django.conf import settings
from django.shortcuts import get_object_or_404, redirect, render
from orders.models import Order

stripe.api_key = settings.STRIPE_SECRET_KEY
stripe.api_version = settings.STRIPE_API_VERSION

# Stripe should NOT calculate anything
USE_AUTOMATIC_TAX = False

def _to_cents(d: Decimal | float | int) -> int:
    return int(Decimal(d).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) * 100)

def payment_process(request):
    """
    Create a Stripe Checkout Session that charges EXACTLY the server-computed order total.
    No Stripe taxes, no Stripe discounts, no Stripe shipping math.
    """
    order_id = request.session.get("order_id")
    order = get_object_or_404(Order, id=order_id)

    if request.method == "POST":
        # Compute your final total on the server (authoritative)
        # prefer explicit total_amount field if you store it; else derive
        total_amount = (
            getattr(order, "total_amount", None)
            if getattr(order, "total_amount", None) is not None
            else (Decimal(order.subtotal_amount or 0)
                  - Decimal(order.discount_amount or 0)
                  + Decimal(order.shipping_amount or 0)
                  + Decimal(order.tax_amount or 0))
        )
        total_cents = _to_cents(total_amount)

        success_url = f"{settings.FRONTEND_URL}/order/thank-you?order={order.id}"
        cancel_url  = f"{settings.FRONTEND_URL}/checkout"

        session_data = {
            "mode": "payment",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "client_reference_id": str(order.id),
            "customer_email": getattr(order, "email", None) or None,

            # Collect addresses for your records only (won't affect price)
            "billing_address_collection": "required",
            "shipping_address_collection": {"allowed_countries": ["US"]},

            # One line item: the exact grand total you computed
            "line_items": [
                {
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": total_cents,
                        "product_data": {
                            "name": f"Order #{order.id}",
                        },
                    },
                    "quantity": 1,
                }
            ],

            # Make sure Stripe does no math
            "automatic_tax": {"enabled": False},
            "allow_promotion_codes": False,

            "metadata": {"order_id": str(order.id)},
        }

        session = stripe.checkout.Session.create(**session_data)
        return redirect(session.url, code=303)

    # GET: optional server-rendered page (unchanged)
    return render(
        request,
        "payment/process.html",
        {"order": order, "steps": ["Cart", "Shipping", "Payment", "Review"], "current_step": 3},
    )


def payment_completed(request):
    return render(
        request,
        "payment/completed.html",
        {"steps": ["Cart", "Shipping", "Payment", "Review"], "current_step": 4},
    )


def payment_canceled(request):
    return render(request, "payment/canceled.html")


def redirect_home(request):
    return redirect("shop:product_list")
