# shipping/models.py
from __future__ import annotations

from decimal import Decimal
from django.db import models


class ShippingRule(models.Model):
    """
    Dynamic shipping rule, matched by:
      - country (e.g. "US")
      - optional state (e.g. "CO")
      - optional postal prefix (first 3–5 digits of ZIP)
      - subtotal range
      - optional method ("standard", "expedited", etc.)
    """

    country = models.CharField(
        max_length=2,
        default="US",
        help_text="ISO country code, e.g. US",
    )
    state = models.CharField(
        max_length=8,
        blank=True,
        default="",
        help_text="State code, e.g. CO. Leave blank for 'any state'.",
    )
    postal_prefix = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text="ZIP / postal prefix (e.g. 800, 802). Leave blank for 'any ZIP'.",
    )

    min_subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Minimum merchandise subtotal (after discount) for this rule.",
    )
    max_subtotal = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum merchandise subtotal, or null for no upper limit.",
    )

    method = models.CharField(
        max_length=32,
        default="standard",
        help_text="e.g. standard, expedited, overnight.",
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        help_text="Shipping price in store currency.",
    )

    priority = models.PositiveIntegerField(
        default=0,
        help_text="Higher priority wins when multiple rules match.",
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["-priority", "min_subtotal"]

    def __str__(self):
        label = f"{self.country}"
        if self.state:
            label += f"-{self.state}"
        if self.postal_prefix:
            label += f" {self.postal_prefix}*"
        return f"{label} [{self.method}] ${self.price} ({self.min_subtotal}–{self.max_subtotal or '∞'})"
