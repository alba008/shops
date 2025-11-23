# orders/tax_utils.py
from decimal import Decimal, ROUND_HALF_UP

FIXED_CO_RATE = Decimal("0.08")  # 8% everywhere


def compute_tax(
    *,
    subtotal: Decimal,
    discount: Decimal,
    state: str = "",
    country: str = "US",
):
    """
    Fixed 8% tax based on business location (Colorado),
    regardless of where the customer is.

    Returns: (tax_amount, tax_rate)
    """
    base = (subtotal or Decimal("0.00")) - (discount or Decimal("0.00"))
    if base < 0:
        base = Decimal("0.00")

    rate = FIXED_CO_RATE               # always 8%
    tax_amount = (base * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return tax_amount, rate
