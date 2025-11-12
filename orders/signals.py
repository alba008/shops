from __future__ import annotations
from django.conf import settings
from django.db import transaction
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from .models import Order

def _money(v) -> str:
    try:
        return f"${float(v):,.2f}"
    except Exception:
        return "$0.00"

def _build_ctx(order: Order) -> dict:
    """
    Re-load the order with items & products to ensure we have current line data
    even if this function is called in a fresh process or after commit.
    """
    from .models import Order as OrderModel  # local import to avoid signal import cycles
    o = (
        OrderModel.objects
        .prefetch_related("items__product")
        .select_related("coupon")
        .get(pk=order.pk)
    )

    # Items context (ensure we use the snapshot fields stored on OrderItem)
    items_ctx = []
    for it in o.items.all():
        price = getattr(it, "price", 0) or 0
        line_total = getattr(it, "get_cost", lambda: price * getattr(it, "quantity", 0))()
        items_ctx.append({
            "product": str(getattr(it, "product", "")) or getattr(it, "product_name", "") or "Item",
            "quantity": getattr(it, "quantity", 0) or 0,
            "price_display": _money(price),
            "line_total_display": _money(line_total),
        })

    # Totals via model helpers; fall back defensively
    try:    subtotal = o.get_total_cost_before_discount()
    except: subtotal = sum([(getattr(x, "price", 0) or 0) * (getattr(x, "quantity", 0) or 0) for x in o.items.all()])
    try:    discount = o.get_discount()
    except: discount = 0
    try:    total = o.get_total_cost()
    except: total = subtotal - (discount or 0)

    return {
        "order": o,
        "items": items_ctx,
        "subtotal_display": _money(subtotal),
        "discount_display": _money(discount),
        "total_display": _money(total),
        "coupon_code": getattr(o.coupon, "code", ""),
        "site_name": getattr(settings, "SITE_NAME", "Shop"),
        "site_domain": getattr(settings, "SITE_DOMAIN", "example.com"),
        "frontend_url": getattr(settings, "FRONTEND_URL", ""),
    }

def _send_email(subject: str, to_email: str, txt_tmpl: str, html_tmpl: str, ctx: dict):
    if not to_email:
        return
    txt = render_to_string(txt_tmpl, ctx)
    html = render_to_string(html_tmpl, ctx)
    m = EmailMultiAlternatives(subject, txt, settings.DEFAULT_FROM_EMAIL, [to_email])
    m.attach_alternative(html, "text/html")
    m.send(fail_silently=False)

# -------------------------------
# PRE-SAVE: remember prior 'paid'
# -------------------------------
@receiver(pre_save, sender=Order)
def _remember_paid(sender, instance: Order, **kwargs):
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._was_paid = bool(old.paid)
        except sender.DoesNotExist:
            instance._was_paid = False
    else:
        instance._was_paid = False

# ---------------------------------------------
# POST-SAVE: created => send "Order received"
# ---------------------------------------------
@receiver(post_save, sender=Order)
def _send_on_created(sender, instance: Order, created: bool, **kwargs):
    if not created:
        return

    # Defer until after the whole transaction (order + items) is committed,
    # so totals and items are present when we render the email.
    def _after_commit():
        ctx = _build_ctx(instance)

        # If items are still empty, quietly skip to avoid "$0.00" emails.
        # (Front-end can re-POST or webhook/another save will re-trigger.)
        if not ctx["items"]:
            return

        subj = f"{ctx['site_name']}: Order #{instance.id} received"
        _send_email(
            subj,
            getattr(instance, "email", None),
            "emails/order_created_buyer.txt",
            "emails/order_created_buyer.html",
            ctx,
        )

        # Optional: notify seller on creation as well
        seller_email = getattr(settings, "ORDERS_SELLER_EMAIL", settings.DEFAULT_FROM_EMAIL)
        if seller_email:
            subj2 = f"{ctx['site_name']}: New order #{instance.id}"
            _send_email(
                subj2,
                seller_email,
                "emails/order_created_seller.txt",
                "emails/order_created_seller.html",
                ctx,
            )

    transaction.on_commit(_after_commit)

# -----------------------------------------------------------
# POST-SAVE: paid flipped False -> True => "Payment confirmed"
# -----------------------------------------------------------
@receiver(post_save, sender=Order)
def _send_on_paid(sender, instance: Order, created: bool, **kwargs):
    # Only when transitioned from unpaid -> paid
    if not (instance.paid and not getattr(instance, "_was_paid", False)):
        return

    def _after_commit():
        ctx = _build_ctx(instance)
        subj = f"{ctx['site_name']}: Order #{instance.id} confirmed"
        _send_email(
            subj,
            getattr(instance, "email", None),
            "emails/order_buyer.txt",
            "emails/order_buyer.html",
            ctx,
        )
        seller_email = getattr(settings, "ORDERS_SELLER_EMAIL", settings.DEFAULT_FROM_EMAIL)
        if seller_email:
            subj2 = f"{ctx['site_name']}: Payment received for order #{instance.id}"
            _send_email(
                subj2,
                seller_email,
                "emails/order_seller.txt",
                "emails/order_seller.html",
                ctx,
            )

    transaction.on_commit(_after_commit)
