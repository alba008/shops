# orders/views_public.py
from decimal import Decimal
from django.http import JsonResponse, Http404
from django.views.decorators.http import require_GET
from django.db.models import F, Value, CharField
from django.db.models.functions import Coalesce, Cast

# DRF imports for the authenticated "my orders" endpoint
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response


def D(x):
    try:
        return Decimal(str(x))
    except Exception:
        return Decimal("0")


def _items_payload(order_id):
    from .models import OrderItem
    qs = (
        OrderItem.objects
        .filter(order_id=order_id)
        .select_related("product")
        .annotate(
            name=F("product__name"),
            product_image=Coalesce(
                Cast(F("product__image_url"), CharField()),
                Cast(F("product__image"), CharField()),
                Value(None, output_field=CharField()),
                output_field=CharField(),
            ),
        )
        .values("product_id", "name", "price", "quantity", "product_image")
    )
    items = []
    subtotal = Decimal("0")
    for it in qs:
        price = D(it.get("price"))
        qty = D(it.get("quantity") or 0)
        line_total = price * qty
        items.append({
            "product_id": it.get("product_id"),
            "name": it.get("name"),
            "price": str(price),
            "quantity": int(qty) if qty == int(qty) else float(qty),
            "line_total": str(line_total),
            "product_image": it.get("product_image") or None,
        })
        subtotal += line_total
    return items, subtotal


def _order_payload(order, include_contact=False):
    # Prefer persisted fields (if present), fall back to derived values
    items, derived_subtotal = _items_payload(order.id)

    subtotal_amount = getattr(order, "subtotal_amount", None) or derived_subtotal
    discount_amount = getattr(order, "discount_amount", None) or D(getattr(order, "discount", 0))
    shipping_amount = getattr(order, "shipping_amount", None) or D(0)
    tax_amount      = getattr(order, "tax_amount", None) or D(0)
    total_amount    = getattr(order, "total_amount", None) \
                      or max(Decimal("0"), subtotal_amount - discount_amount) + shipping_amount + tax_amount
    tax_rate        = getattr(order, "tax_rate", None)

    payload = {
        "id": order.id,
        "paid": getattr(order, "paid", None),
        "created": getattr(order, "created", None).isoformat() if getattr(order, "created", None) else None,
        "updated": getattr(order, "updated", None).isoformat() if getattr(order, "updated", None) else None,
        "items": items,

        # persisted amounts
        "subtotal_amount": str(subtotal_amount),
        "discount_amount": str(discount_amount),
        "shipping_amount": str(shipping_amount),
        "tax_rate": str(tax_rate) if tax_rate is not None else None,
        "tax_amount": str(tax_amount),
        "total_amount": str(total_amount),

        # legacy mirrors for your FE helpers
        "subtotal": str(subtotal_amount),
        "discount": str(discount_amount),
        "shipping": str(shipping_amount),
        "tax": str(tax_amount),
        "total": str(total_amount),
    }

    if include_contact:
        payload.update({
            "first_name": getattr(order, "first_name", None),
            "last_name": getattr(order, "last_name", None),
            "email": getattr(order, "email", None),
            "address": getattr(order, "address", None),
            "postal_code": getattr(order, "postal_code", None),
            "city": getattr(order, "city", None),
            # Optional: expose shipping inputs so you can debug
            "ship_state": getattr(order, "ship_state", None),
            "ship_country": getattr(order, "ship_country", None),
            "shipping_method": getattr(order, "shipping_method", None),
        })

    return payload


# ---------- NEW: authenticated "my orders" endpoint ----------
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def my_orders(request):
    """
    Return recent orders for the logged-in user.

    - Prefer the FK user field if present (Order.user)
    - Fallback to email match if no user-linked orders exist
    """
    from .models import Order

    user = request.user
    qs = Order.objects.none()

    # Prefer FK match if model has a user field and requests are linked
    if user.is_authenticated:
        try:
            qs = Order.objects.filter(user=user).order_by("-created")
        except Exception:
            qs = Order.objects.none()

    # Fallback: look up by email if no FK matches
    if not qs.exists() and getattr(user, "email", None):
        qs = Order.objects.filter(email__iexact=user.email).order_by("-created")

    qs = qs[:20]  # latest 20 orders

    data = []
    for o in qs:
        # Compute or reuse totals in the same way as _order_payload
        subtotal_amount = getattr(o, "subtotal_amount", None)
        if subtotal_amount is None:
            _, derived_subtotal = _items_payload(o.id)
            subtotal_amount = derived_subtotal

        discount_amount = getattr(o, "discount_amount", None) or D(getattr(o, "discount", 0))
        shipping_amount = getattr(o, "shipping_amount", None) or D(0)
        tax_amount      = getattr(o, "tax_amount", None) or D(0)

        total_amount = getattr(o, "total_amount", None)
        if total_amount is None:
            total_amount = max(Decimal("0"), subtotal_amount - discount_amount) + shipping_amount + tax_amount

        data.append({
            "id": o.id,
            "created": getattr(o, "created", None).isoformat() if getattr(o, "created", None) else None,
            "total_amount": str(total_amount),
            "status": getattr(o, "status", None)
                      or getattr(o, "payment_status", None)
                      or ("Paid" if getattr(o, "paid", False) else "Pending"),
        })

    return Response(data)


@require_GET
def order_detail_public(request, pk: int):
    from .models import Order
    try:
        order = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        raise Http404
    include_contact = request.GET.get("full") in {"1", "true", "yes"}
    return JsonResponse(_order_payload(order, include_contact), status=200)


@require_GET
def order_items_public(request, pk: int):
    items, _ = _items_payload(pk)
    return JsonResponse(items, safe=False, status=200)


@require_GET
def last_order(request):
    oid = request.session.get("last_order_id")
    if not oid:
        return JsonResponse({"detail": "No recent order"}, status=404)
    from .models import Order
    try:
        order = Order.objects.get(pk=oid)
    except Order.DoesNotExist:
        return JsonResponse({"detail": "Order not found"}, status=404)
    include_contact = request.GET.get("full") in {"1", "true", "yes"}
    return JsonResponse(_order_payload(order, include_contact), status=200)
