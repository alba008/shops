# shop/stripe_views.py
from __future__ import annotations
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt


import hashlib
import json as _json
from decimal import Decimal, ROUND_HALF_UP

import stripe
from django.conf import settings
from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import AllowAny

stripe.api_key = settings.STRIPE_SECRET_KEY
CURRENCY = "usd"

def _to_cents(v) -> int:
    try:
        d = Decimal(v).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return int(d * 100)
    except Exception:
        return 0

# ---------- API: create checkout session (charge server-computed grand total) ----------
@api_view(["POST"])
@permission_classes([AllowAny])
@authentication_classes([])  # don't require SessionAuthentication/CSRF for this endpoint
def create_stripe_session(request):
    """
    POST { "order_id": 123 }

    Creates a Checkout Session that charges EXACTLY the server-computed grand total
    stored on the Order (`total_amount`). Stripe collects addresses for your records,
    but does NOT change the price (no Automatic Tax, no shipping math, no discounts).
    """
    # ---- parse body safely ----
    def _safe_json_body(req):
        try:
            return req.data or {}
        except Exception:
            try:
                return _json.loads(req.body or "{}")
            except Exception:
                return {}

    data = _safe_json_body(request)
    order_id = data.get("order_id") or request.session.get("last_order_id")
    if not order_id:
        return JsonResponse({"detail": "No order_id provided."}, status=400)

    # ---- load order & ensure totals exist ----
    from orders.models import Order
    try:
        order = Order.objects.get(id=order_id, paid=False)
    except Order.DoesNotExist:
        return JsonResponse({"detail": "Order not found or already paid."}, status=400)

    # If you have a canonical compute step, run it (won’t change final price logic here)
    if hasattr(order, "update_totals"):
        try:
            order.update_totals(save=True)
        except Exception:
            # continue; we will use whatever is persisted already
            pass

    # Require a persisted total_amount
    if not hasattr(order, "total_amount") or order.total_amount is None:
        return JsonResponse({"detail": "Order total_amount is missing. Compute totals before checkout."}, status=400)

    total_cents = _to_cents(order.total_amount)
    if total_cents <= 0:
        return JsonResponse({"detail": "Order total must be greater than zero."}, status=400)

    # ---- resume existing open session if we already created one for same order+total ----
    # The cache key includes total_cents so if the total changes, a new session will be created.
    session_cache_key = f"checkout_session:{order.id}:{total_cents}"
    prior_session_id = request.session.get(session_cache_key)
    if prior_session_id:
        try:
            prior = stripe.checkout.Session.retrieve(prior_session_id)
            if prior and prior.get("status") == "open" and prior.get("payment_status") == "unpaid":
                return JsonResponse({"url": prior["url"]}, status=200)
        except Exception:
            pass  # just create a new one below

    # ---- fixed-price single line item (NO automatic tax, NO shipping options, NO discounts) ----
    site_name = getattr(settings, "SITE_NAME", "Store")
    title = f"Order #{order.id} — {site_name}"

    line_items = [{
        "quantity": 1,
        "price_data": {
            "currency": CURRENCY,
            "unit_amount": total_cents,
            "product_data": {
                "name": title,
                # You can show a generic image on Stripe (optional):
                # "images": ["https://sockcs.com/logo.png"],
            },
        },
    }]

    # Collect addresses just for your records (has no price impact now)
    billing_address_collection = "required"
    shipping_address_collection = {"allowed_countries": ["US"]}

    # Absolutely disable any Stripe-side price math
    automatic_tax = {"enabled": False}
    allow_promotion_codes = False
    discounts = None
    shipping_options = None  # no shipping rates from Stripe; price is already final

    frontend = getattr(settings, "FRONTEND_URL", "https://sockcs.com").rstrip("/")
    success_url = f"{frontend}/order/thank-you?order={order.id}"
    cancel_url = f"{frontend}/cart"

    # Idempotency key: unique to (order, total_cents)
    fp_src = _json.dumps({"oid": order.id, "total": total_cents}, sort_keys=True, separators=(",", ":"))
    idem_key = f"fixedtotal:{hashlib.sha1(fp_src.encode()).hexdigest()[:20]}"

    # ---- create session ----
    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            client_reference_id=str(order.id),
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=(order.email or None),
            line_items=line_items,
            # Collections for records only
            billing_address_collection=billing_address_collection,
            shipping_address_collection=shipping_address_collection,
            # Absolutely no Stripe calculations
            automatic_tax=automatic_tax,
            allow_promotion_codes=allow_promotion_codes,
            # Explicitly pass None for options we don't use
            discounts=discounts,
            shipping_options=shipping_options,
            metadata={
                "order_id": str(order.id),
                "charged_total_cents": str(total_cents),
                "charged_total_display": f"${Decimal(total_cents)/Decimal(100):.2f}",
                "source": "fixed-total-checkout",
            },
            idempotency_key=idem_key,
        )

        # cache the session id for quick resume
        request.session[session_cache_key] = session.id
        request.session["last_order_id"] = order.id
        request.session.modified = True

        return JsonResponse({"url": session.url}, status=201)

    except stripe.error.StripeError as e:
        return JsonResponse({"detail": str(e)}, status=400)


@csrf_exempt
def stripe_webhook(request):
    """
    Verify Stripe signature, parse event, and handle the few events you care about.
    Make sure STRIPE_WEBHOOK_SECRET is set in your environment/settings.
    """
    endpoint_secret = getattr(settings, "STRIPE_WEBHOOK_SECRET", "")
    payload = request.body
    sig_header = request.META.get("HTTP_STRIPE_SIGNATURE", "")

    try:
        event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
    except ValueError:
        return HttpResponse(status=400)  # invalid payload
    except stripe.error.SignatureVerificationError:
        return HttpResponse(status=400)  # invalid signature

    # --- Handle events you care about ---
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        # Example: mark order as paid
        order_id = session.get("client_reference_id")
        if order_id:
            try:
                from orders.models import Order
                order = Order.objects.get(id=order_id)
                # You can also check session["payment_status"] == "paid"
                order.paid = True
                order.save(update_fields=["paid"])
            except Order.DoesNotExist:
                pass

    # You can also handle 'payment_intent.succeeded' etc. if needed.

    return HttpResponse(status=200)
