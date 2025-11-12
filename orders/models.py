from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.utils.translation import gettext_lazy as _
from coupons.models import Coupon


# ------- Config (move to settings if you prefer) -------
FREE_SHIP_THRESHOLD = Decimal("50.00")
TAX_ON_SHIPPING = False
STATE_TAX_RATES = {
    "NY": Decimal("0.08875"),
    "NJ": Decimal("0.06625"),
    "CA": Decimal("0.0725"),
}
DEFAULT_TAX_RATE = Decimal("0.00")


class Order(models.Model):
    first_name = models.CharField(_('first name'), max_length=50)
    last_name = models.CharField(_('last name'), max_length=50)
    email = models.EmailField(_('e-mail'))
    address = models.CharField(_('address'), max_length=250)
    postal_code = models.CharField(_('postal code'), max_length=20)
    city = models.CharField(_('city'), max_length=100)

    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    paid = models.BooleanField(default=False)
    stripe_id = models.CharField(max_length=250, blank=True)

    coupon = models.ForeignKey(
        Coupon,
        related_name='orders',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
    )
    discount = models.IntegerField(
        default=0,
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    # --- Shipping / tax context ---
    ship_state = models.CharField(max_length=8, blank=True, default="")          # e.g. "NY"
    ship_country = models.CharField(max_length=2, blank=True, default="US")      # e.g. "US"
    shipping_method = models.CharField(max_length=32, blank=True, default="standard")

    # --- Persisted amounts (server is source of truth) ---
    subtotal_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    discount_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    shipping_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    tax_rate = models.DecimalField(max_digits=6, decimal_places=5, default=Decimal("0.00000"))
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal("0.00"))

    class Meta:
        ordering = ['-created']
        indexes = [models.Index(fields=['-created'])]

    def __str__(self):
        return f'Order {self.id}'

    # ---------------- Legacy helpers (kept for compatibility) ----------------
    def get_total_cost_before_discount(self) -> Decimal:
        return sum(item.get_cost() for item in self.items.all())

    def get_discount(self) -> Decimal:
        total_cost = self.get_total_cost_before_discount()
        if self.discount:
            return total_cost * (Decimal(self.discount) / Decimal(100))
        return Decimal("0.00")

    def get_total_cost(self) -> Decimal:
        """
        Backwards-compatible: merchandise total AFTER % discount (no shipping/tax).
        """
        total_cost = self.get_total_cost_before_discount()
        return total_cost - self.get_discount()

    def get_stripe_url(self):
        if not self.stripe_id:
            return None
        path = '/test/' if '_test_' in settings.STRIPE_SECRET_KEY else '/'
        return f'https://dashboard.stripe.com{path}payments/{self.stripe_id}'

    # ---------------- New calculators (authoritative) ----------------
    def merchandise_subtotal(self) -> Decimal:
        return self.get_total_cost_before_discount().quantize(Decimal("0.01"))

    def merchandise_after_discount(self) -> Decimal:
        return self.get_total_cost().quantize(Decimal("0.01"))

    def compute_shipping(self, merchandise_total: Decimal) -> Decimal:
        method = (self.shipping_method or "standard").lower()
        if method == "standard":
            return Decimal("0.00") if merchandise_total >= FREE_SHIP_THRESHOLD else Decimal("7.95")
        if method == "expedited":
            return Decimal("19.95")
        if method == "overnight":
            return Decimal("34.95")
        return Decimal("0.00")

    def effective_tax_rate(self) -> Decimal:
        if (self.ship_country or "").upper() != "US":
            return DEFAULT_TAX_RATE
        return STATE_TAX_RATES.get((self.ship_state or "").upper(), DEFAULT_TAX_RATE)

    def compute_tax(self, merchandise_total: Decimal, shipping: Decimal) -> Decimal:
        rate = self.effective_tax_rate()
        base = merchandise_total + (shipping if TAX_ON_SHIPPING else Decimal("0.00"))
        return (base * rate).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    def compute_grand_total(self) -> dict:
        subtotal = self.merchandise_subtotal()
        discount_abs = self.get_discount().quantize(Decimal("0.01"))
        merch_after = (subtotal - discount_abs).quantize(Decimal("0.01"))
        shipping = self.compute_shipping(merch_after)
        tax_r = self.effective_tax_rate()
        tax_amt = self.compute_tax(merch_after, shipping)
        grand = (merch_after + shipping + tax_amt).quantize(Decimal("0.01"))
        return {
            "subtotal_amount": subtotal,
            "discount_amount": discount_abs,
            "shipping_amount": shipping,
            "tax_rate": tax_r,
            "tax_amount": tax_amt,
            "total_amount": grand,
        }

    def update_totals(self, save: bool = True):
        comp = self.compute_grand_total()
        self.subtotal_amount = comp["subtotal_amount"]
        self.discount_amount = comp["discount_amount"]
        self.shipping_amount = comp["shipping_amount"]
        self.tax_rate = comp["tax_rate"]
        self.tax_amount = comp["tax_amount"]
        self.total_amount = comp["total_amount"]
        if save:
            self.save(update_fields=[
                "subtotal_amount", "discount_amount", "shipping_amount",
                "tax_rate", "tax_amount", "total_amount",
            ])
        return comp


class OrderItem(models.Model):
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey('shop.Product', related_name='order_items', on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(default=1)

    def __str__(self):
        return str(self.id)

    def get_cost(self) -> Decimal:
        # FIXED: removed stray period and added safe casting
        return (self.price or Decimal("0.00")) * Decimal(int(self.quantity or 0))


# --- Webhook idempotency: store processed Stripe event IDs ---
class StripeEvent(models.Model):
    event_id = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.event_id
