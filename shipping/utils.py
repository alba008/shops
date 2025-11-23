from __future__ import annotations

from decimal import Decimal
from django.db.models import Q

from .models import ShippingRule


def quote_shipping(
    *,
    country: str = "US",
    state: str = "",
    postal_code: str = "",
    subtotal: Decimal = Decimal("0.00"),
    method: str = "standard",
) -> Decimal:
    country = (country or "US").upper()
    state = (state or "").upper()
    postal_code = (postal_code or "").strip()

    try:
        subtotal = Decimal(subtotal)
    except Exception:
        subtotal = Decimal("0.00")

    qs = ShippingRule.objects.filter(is_active=True, country=country)
    qs = qs.filter(Q(state__iexact=state) | Q(state=""))           # state or any
    qs = qs.filter(Q(method__iexact=method) | Q(method=""))       # method or any
    qs = qs.filter(
        min_subtotal__lte=subtotal
    ).filter(
        Q(max_subtotal__isnull=True) | Q(max_subtotal__gte=subtotal)
    )

    if postal_code:
        prefix3 = postal_code[:3]
        prefix5 = postal_code[:5]
        qs = qs.filter(
            Q(postal_prefix="") |
            Q(postal_prefix__iexact=prefix3) |
            Q(postal_prefix__iexact=prefix5)
        )

    rule = qs.order_by("-priority", "min_subtotal").first()
    if rule:
        return rule.price

    # Fallback if nothing matched
    if subtotal >= Decimal("50.00"):
        return Decimal("0.00")
    return Decimal("7.95")
