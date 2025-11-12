# orders/utils.py
from decimal import Decimal

FREE_SHIP_THRESHOLD = Decimal("75.00")
RATES = {"NY": Decimal("0.08875"), "NJ": Decimal("0.06625"), "CA": Decimal("0.0725")}
DEFAULT_TAX = Decimal("0.00")
TAX_ON_SHIPPING = False

def compute_shipping(method: str, merchandise_total: Decimal) -> Decimal:
    if method == "standard":
        return Decimal("0.00") if merchandise_total >= FREE_SHIP_THRESHOLD else Decimal("7.95")
    if method == "expedited":
        return Decimal("19.95")
    if method == "overnight":
        return Decimal("34.95")
    return Decimal("0.00")

def compute_tax(country: str, state: str, merchandise_total: Decimal, shipping: Decimal) -> Decimal:
    if (country or "").upper() != "US":
        return Decimal("0.00")
    rate = RATES.get((state or "").upper(), DEFAULT_TAX)
    base = merchandise_total + (shipping if TAX_ON_SHIPPING else Decimal("0"))
    return (base * rate).quantize(Decimal("0.01"))
