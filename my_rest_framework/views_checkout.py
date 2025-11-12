# my_rest_framework/views_checkout.py
from decimal import Decimal
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import permissions, status
from rest_framework.exceptions import ValidationError

from cart.cart import Cart as SessionCart
from .views_cart import _cart_payload  # reuse your existing payload builder

# OPTIONAL: if using Stripe (recommended)
try:
    import stripe
    stripe.api_key = getattr(settings, "STRIPE_SECRET_KEY", None)
    STRIPE_ENABLED = bool(stripe.api_key)
except Exception:
    stripe = None
    STRIPE_ENABLED = False


def _cart_amount_cents(cart: SessionCart) -> int:
    """
    Convert cart total-after-discount to cents (int). Defaults to subtotal if helper is missing.
    """
    # Try your helpers
    if hasattr(cart, "get_total_price_after_discount"):
        total = cart.get_total_price_after_discount()
    elif hasattr(cart, "get_total_price"):
        total = cart.get_total_price()
    else:
        total = 0
    # Normalize to cents
    try:
        return int(Decimal(total) * 100)
    except Exception:
        return 0


class CreateCheckoutSessionView(APIView):
    """
    POST -> returns client_secret (if Stripe) and the amount (cents) based on the session cart.
    """
    permission_classes = [permissions.AllowAny]  # or IsAuthenticated if you require login

    def post(self, request):
        cart = SessionCart(request)
        amount_cents = _cart_amount_cents(cart)
        if amount_cents <= 0:
            raise ValidationError({"cart": "Cart is empty or total is zero."})

        currency = "usd"

        # If using Stripe, create a PaymentIntent and return its client_secret
        client_secret = None
        payment_intent_id = None

        if STRIPE_ENABLED:
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency,
                automatic_payment_methods={"enabled": True},
                metadata={
                    # (optional) include info to link back to your order/session if needed
                    "session_key": request.session.session_key or "",
                },
            )
            client_secret = intent.client_secret
            payment_intent_id = intent.id

        payload = {
            "amount": amount_cents,
            "currency": currency,
            "client_secret": client_secret,         # may be None if Stripe not configured
            "payment_intent_id": payment_intent_id, # may be None
        }
        return Response(payload, status=status.HTTP_201_CREATED)


class FinalizeCheckoutView(APIView):
    """
    Call this from your success page.
    Option A (simple): trust that you only land here after success -> clear cart.
    Option B (safer): if payment_intent_id is provided and Stripe is enabled, verify it's 'succeeded'.
    Returns the UPDATED cart payload (now empty).
    """
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        cart = SessionCart(request)

        # ------- Option B: verify PaymentIntent if provided -------
        payment_intent_id = request.data.get("payment_intent_id")
        if STRIPE_ENABLED and payment_intent_id:
            try:
                intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            except Exception:
                return Response({"error": "Unable to verify payment intent."}, status=400)

            if getattr(intent, "status", None) != "succeeded":
                # If you have a pending/processing path, handle it here.
                return Response({"error": "Payment not confirmed yet."}, status=409)

        # ------- Option A: if you don’t pass payment_intent_id, we clear anyway -------
        cart.clear()
        request.session.modified = True

        return Response(_cart_payload(cart), headers={"Cache-Control": "no-store"})
