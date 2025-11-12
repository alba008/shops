# orders/views.py
import weasyprint
from django.contrib.staticfiles import finders
from cart.cart import Cart
from django.shortcuts import get_object_or_404, redirect, render
from .forms import OrderCreateForm
from .models import Order, OrderItem
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest
from django.template.loader import render_to_string

from .tasks import order_created
from django.contrib.admin.views.decorators import staff_member_required

# NEW: only needed if your Order model doesn't have update_totals()
from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt

try:
    # prefer your centralized utils if update_totals is absent
    from .utils import compute_shipping, compute_tax
except Exception:
    compute_shipping = compute_tax = None


def _to_dec(x) -> Decimal:
    return Decimal(str(x or "0")).quantize(Decimal("0.01"))

def _state_from_address(addr: dict) -> str:
    st = (addr or {}).get("state") or (addr or {}).get("region") or ""
    return str(st).strip().upper()[:2]

def _fallback_shipping(method: str, merchandise_after: Decimal) -> Decimal:
    # Replace with your shipping module if available
    if method == "express":
        return Decimal("14.00")
    if merchandise_after >= Decimal("100.00"):
        return Decimal("0.00")
    return Decimal("6.00")

def _fallback_tax(country: str, state: str, taxable_base: Decimal, shipping: Decimal) -> Decimal:
    # Adjust whether shipping is taxable for your business; here: goods only
    rate = _to_dec(getattr(settings, "TAX_RATES", {}).get(state, Decimal("0.00")))
    return (taxable_base * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def order_create(request):
    cart = Cart(request)

    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save(commit=False)

            # --- coupon/discount (existing) ---
            if cart.coupon:
                order.coupon = cart.coupon
                order.discount = cart.coupon.discount  # % value

            # --- capture shipping inputs if present ---
            order.shipping_method = (request.POST.get('shipping_method') or 'standard').lower()
            order.ship_state = (request.POST.get('state') or '').upper()
            order.ship_country = (request.POST.get('country') or 'US').upper()

            order.save()

            # create items (existing)
            for item in cart:
                OrderItem.objects.create(
                    order=order,
                    product=item['product'],
                    price=item['price'],
                    quantity=item['quantity']
                )

            # --- compute & persist authoritative amounts for Stripe/email/thank-you ---
            if hasattr(order, 'update_totals'):
                order.update_totals(save=True)
            else:
                subtotal_amount = order.get_total_cost_before_discount().quantize(Decimal('0.01'))
                discount_amount = order.get_discount().quantize(Decimal('0.01'))
                merchandise_after = (subtotal_amount - discount_amount).quantize(Decimal('0.01'))

                # SHIPPING
                if compute_shipping:
                    shipping_amount = compute_shipping(order.shipping_method, merchandise_after)
                else:
                    shipping_amount = _fallback_shipping(order.shipping_method, merchandise_after)
                shipping_amount = _to_dec(shipping_amount)

                # TAX
                if compute_tax:
                    tax_amount = compute_tax(order.ship_country or "US", order.ship_state or "", merchandise_after, shipping_amount)
                else:
                    tax_amount = _fallback_tax(order.ship_country or "US", order.ship_state or "", merchandise_after, shipping_amount)
                tax_amount = _to_dec(tax_amount)

                total_amount = (merchandise_after + shipping_amount + tax_amount).quantize(Decimal('0.01'))

                for attr, val in [
                    ('subtotal_amount', subtotal_amount),
                    ('discount_amount', discount_amount),
                    ('shipping_amount', shipping_amount),
                    ('tax_amount', tax_amount),
                    ('total_amount', total_amount),
                ]:
                    if hasattr(order, attr):
                        setattr(order, attr, val)
                order.save()

            # clear the cart (existing)
            cart.clear()

            # async email/notification (existing)
            order_created.delay(order.id)

            # keep same payment handoff (existing)
            request.session['order_id'] = order.id
            return redirect('payment:process')

    else:
        form = OrderCreateForm()

    return render(
        request,
        'orders/order/create.html',
        {
            'cart': cart,
            'form': form,
            'current_step': 2,
            'steps': ['Cart', 'Shipping', 'Payment', 'Review'],
        }
    )


@staff_member_required
def admin_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    return render(request, 'admin/orders/order/detail.html', {'order': order})


@staff_member_required
def admin_order_pdf(request, order_id):
    order = get_object_or_404(Order, id=order_id)
    html = render_to_string('orders/order/pdf.html', {'order': order})
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'filename=order_{order.id}.pdf'
    weasyprint.HTML(string=html).write_pdf(
        response,
        stylesheets=[weasyprint.CSS(finders.find('css/pdf.css'))],
    )
    return response


# ---------- NEW: price the order after address/method are entered ----------
@csrf_exempt  # if you prefer CSRF, remove this and POST with X-CSRFToken from the SPA
@require_POST
def price_order(request, order_id: int):
    """
    POST JSON: {
      "shipping_address": { "state": "NY", ... },
      "shipping_method": "standard" | "express"
    }
    Computes shipping + tax, persists subtotal/discount/shipping/tax/total on order,
    and returns the snapshot for the checkout UI & emails.
    """
    import json
    try:
        body = json.loads(request.body.decode("utf-8"))
    except Exception:
        return HttpResponseBadRequest("Invalid JSON")

    order = get_object_or_404(Order, id=order_id)

    # incoming data
    addr = body.get("shipping_address") or {}
    method = (body.get("shipping_method") or order.shipping_method or "standard").lower()
    state = _state_from_address(addr)
    country = (addr.get("country") or order.ship_country or "US").upper()

    # persist method/state if model has the fields
    if hasattr(order, "shipping_method"):
        order.shipping_method = method
    if hasattr(order, "ship_state"):
        order.ship_state = state
    if hasattr(order, "ship_country"):
        order.ship_country = country

    # subtotal/discount from items
    subtotal_amount = _to_dec(getattr(order, "subtotal_amount", None) or order.get_total_cost_before_discount())
    discount_amount = _to_dec(getattr(order, "discount_amount", None) or order.get_discount())
    merchandise_after = _to_dec(subtotal_amount - discount_amount)

    # shipping
    if compute_shipping:
        shipping_amount = _to_dec(compute_shipping(method, merchandise_after))
    else:
        shipping_amount = _fallback_shipping(method, merchandise_after)

    # tax (goods only; adjust if shipping taxable in your region)
    if compute_tax:
        tax_amount = _to_dec(compute_tax(country, state, merchandise_after, shipping_amount))
    else:
        tax_amount = _fallback_tax(country, state, merchandise_after, shipping_amount)

    total_amount = _to_dec(merchandise_after + shipping_amount + tax_amount)

    # persist authoritative snapshot
    for attr, val in [
        ('subtotal_amount', subtotal_amount),
        ('discount_amount', discount_amount),
        ('shipping_amount', shipping_amount),
        ('tax_amount', tax_amount),
        ('total_amount', total_amount),
    ]:
        if hasattr(order, attr):
            setattr(order, attr, val)
    order.save()

    return JsonResponse({
        "order_id": order.id,
        "state": state,
        "subtotal_amount": str(subtotal_amount),
        "discount_amount": str(discount_amount),
        "shipping_amount": str(shipping_amount),
        "tax_amount": str(tax_amount),
        "total_amount": str(total_amount),
        "shipping_method": method,
        "tax_rate": str(getattr(settings, "TAX_RATES", {}).get(state, Decimal("0.00"))),
    })
