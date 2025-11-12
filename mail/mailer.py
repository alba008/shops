from typing import Dict, Optional, Sequence
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

from .adapters import (
    get_buyer_email, get_buyer_name, get_order_number, get_total_display, get_seller_recipients
)

def render_subject(subject: str) -> str:
    return f"{getattr(settings, 'SITE_NAME', 'Our Store')}: {subject}"

def send_templated_email(
    *,
    to: Sequence[str],
    subject: str,
    template_base: str,  # e.g. "emails/order_buyer"
    context: Optional[Dict] = None,
    from_email: Optional[str] = None,
    bcc: Optional[Sequence[str]] = None,
    reply_to: Optional[Sequence[str]] = None,
) -> int:
    ctx = {
        "site_name": getattr(settings, "SITE_NAME", "Our Store"),
        "site_domain": getattr(settings, "SITE_DOMAIN", "example.com"),
        "frontend_url": getattr(settings, "FRONTEND_URL", ""),
        **(context or {}),
    }
    text_body = render_to_string(f"{template_base}.txt", ctx)
    html_body = render_to_string(f"{template_base}.html", ctx)

    msg = EmailMultiAlternatives(
        subject=render_subject(subject),
        body=text_body,
        from_email=from_email or settings.DEFAULT_FROM_EMAIL,
        to=list(to),
        bcc=list(bcc) if bcc else None,
        reply_to=list(reply_to) if reply_to else None,
    )
    msg.attach_alternative(html_body, "text/html")
    return msg.send(fail_silently=False)

def send_order_buyer(order):
    to_email = get_buyer_email(order)
    if not to_email:
        return 0
    ctx = {
        "order": order,
        "order_number": get_order_number(order),
        "order_total_display": get_total_display(order),
        "buyer_name": get_buyer_name(order),
    }
    return send_templated_email(
        to=[to_email],
        subject=f"Order #{ctx['order_number']} confirmed",
        template_base="emails/order_buyer",
        context=ctx,
    )

def send_order_seller(order):
    recipients = [e for e in get_seller_recipients(order) if e]
    if not recipients:
        return 0
    ctx = {
        "order": order,
        "order_number": get_order_number(order),
        "order_total_display": get_total_display(order),
        "buyer_email": get_buyer_email(order),
        "buyer_name": get_buyer_name(order),
    }
    return send_templated_email(
        to=recipients,
        subject=f"New order #{ctx['order_number']}",
        template_base="emails/order_seller",
        context=ctx,
    )
