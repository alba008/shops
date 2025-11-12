# orders/admin.py
import csv
from io import StringIO
from datetime import datetime

from django.http import HttpResponse
from django.contrib import admin, messages
from django.urls import reverse, NoReverseMatch
from django.utils.safestring import mark_safe
from django.utils import timezone

from .models import Order, OrderItem


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    raw_id_fields = ["product"]
    extra = 0


@admin.display(description="Stripe payment", ordering="stripe_id")
def order_payment(obj: Order):
    if getattr(obj, "stripe_id", None):
        url = getattr(obj, "get_stripe_url", lambda: None)()
        if url:
            return mark_safe(f'<a href="{url}" target="_blank" rel="noopener">{obj.stripe_id}</a>')
        return obj.stripe_id
    return "—"


@admin.display(description="Detail")
def order_detail(obj: Order):
    try:
        url = reverse("orders:admin_order_detail", args=[obj.pk])
        return mark_safe(f'<a href="{url}">View</a>')
    except NoReverseMatch:
        return "—"


@admin.display(description="Invoice")
def order_pdf(obj: Order):
    try:
        url = reverse("orders:admin_order_pdf", args=[obj.pk])
        return mark_safe(f'<a href="{url}">PDF</a>')
    except NoReverseMatch:
        return "—"


@admin.action(description="Export selected to CSV")
def export_to_csv(modeladmin, request, queryset):
    opts = modeladmin.model._meta
    fields = [f for f in opts.get_fields() if not f.many_to_many and not f.one_to_many]

    buff = StringIO()
    writer = csv.writer(buff)
    writer.writerow([f.verbose_name for f in fields])

    for obj in queryset:
        row = []
        for f in fields:
            value = f.value_from_object(obj)
            if isinstance(value, datetime):
                if timezone.is_naive(value):
                    value = timezone.make_aware(value, timezone.get_current_timezone())
                value = timezone.localtime(value).strftime("%Y-%m-%d %H:%M:%S")
            row.append(value)
        writer.writerow(row)

    response = HttpResponse(buff.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{opts.model_name}_export.csv"'
    return response


@admin.action(description="Mark selected as paid")
def mark_paid(modeladmin, request, queryset):
    updated = queryset.update(paid=True)
    modeladmin.message_user(request, f"{updated} order(s) marked as paid.", level=messages.SUCCESS)


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        "id", "first_name", "last_name", "email",
        "address", "postal_code", "city",
        "paid", order_payment, "created", "updated",
        order_detail, order_pdf,
    ]
    list_display_links = ("id", "first_name", "last_name")
    list_filter = ["paid", "created", "updated"]
    search_fields = ["id", "first_name", "last_name", "email", "address", "city", "postal_code"]
    date_hierarchy = "created"
    readonly_fields = ["created", "updated"]
    inlines = [OrderItemInline]
    actions = [export_to_csv, mark_paid]
    list_per_page = 50
    ordering = ("-created",)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related("items__product")


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "product", "price", "quantity")
    raw_id_fields = ("order", "product")
    search_fields = ("order__id", "product__name")
    list_select_related = ("order", "product")
