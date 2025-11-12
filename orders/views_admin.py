# orders/views_admin.py
from decimal import Decimal
from datetime import timedelta

from django.db.models import Sum, F, DecimalField, Count
from django.db.models.functions import TruncDate, Coalesce
from django.utils import timezone

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView

from .models import Order, OrderItem
from .serializers_admin import OrderListSer, OrderDetailAdminSer

MONEY = DecimalField(max_digits=12, decimal_places=2)

def revenue_expr():
    # If your reverse name isn't "items", use "orderitem__price" etc.
    return Coalesce(Sum(F("items__price") * F("items__quantity"), output_field=MONEY), Decimal("0.00"))

@api_view(["GET"])
@permission_classes([IsAdminUser])
def stats(request):
    tz = timezone.get_current_timezone()
    now = timezone.now().astimezone(tz)
    start_today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    start_7d = start_today - timedelta(days=7)

    today_qs = Order.objects.filter(created__gte=start_today, paid=True)
    week_qs  = Order.objects.filter(created__gte=start_7d, created__lt=start_today, paid=True)

    revenue_today = today_qs.aggregate(v=revenue_expr())["v"] or Decimal("0.00")
    orders_today  = today_qs.count()

    rev_7d = week_qs.aggregate(v=revenue_expr())["v"] or Decimal("0.00")
    ord_7d = week_qs.count()

    return Response({
        "revenue_today": revenue_today,
        "orders_today": orders_today,
        "revenue_avg_7d": (rev_7d / Decimal("7")) if rev_7d else Decimal("0.00"),
        "orders_avg_7d": (ord_7d / 7) if ord_7d else 0,
        "aov_7d": (rev_7d / Decimal(ord_7d)) if ord_7d else None,
        "conv_rate_7d": None,  # needs traffic analytics to compute
        "customers_today": today_qs.values("email").distinct().count(),
    })

def sales_range(days: int):
    since = timezone.now() - timedelta(days=days)
    qs = (Order.objects.filter(created__gte=since, paid=True)
          .annotate(day=TruncDate("created"))
          .values("day")
          .annotate(revenue=revenue_expr(), orders=Count("id"))
          .order_by("day"))
    return [{"day": r["day"].isoformat(), "revenue": r["revenue"], "orders": r["orders"]} for r in qs]

@api_view(["GET"])
@permission_classes([IsAdminUser])
def sales_7d(request):  return Response(sales_range(7))

@api_view(["GET"])
@permission_classes([IsAdminUser])
def sales_30d(request): return Response(sales_range(30))

class StdPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 200

class OrderList(ListAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = OrderListSer
    pagination_class = StdPagination

    def get_queryset(self):
        qs = Order.objects.all().order_by("-created")
        paid = self.request.query_params.get("paid")
        if paid in {"true","1","false","0"}:
            qs = qs.filter(paid=(paid in {"true","1"}))
        return qs

class OrderDetail(RetrieveAPIView):
    permission_classes = [IsAdminUser]
    serializer_class = OrderDetailAdminSer
    queryset = Order.objects.all()

@api_view(["POST"])
@permission_classes([IsAdminUser])
def mark_paid(request, pk: int):
    try:
        o = Order.objects.get(pk=pk)
    except Order.DoesNotExist:
        return Response({"detail":"Not found"}, status=404)
    if not o.paid:
        o.paid = True
        o.save(update_fields=["paid"])
    return Response({"status":"ok"})

@api_view(["GET"])
@permission_classes([IsAdminUser])
def top_products(request):
    days = int(request.query_params.get("days", 30))
    limit = int(request.query_params.get("limit", 5))
    since = timezone.now() - timedelta(days=days)

    qs = (OrderItem.objects.filter(order__paid=True, order__created__gte=since)
          .values("product__name")
          .annotate(
              units=Coalesce(Sum("quantity"), 0),
              revenue=Coalesce(Sum(F("price")*F("quantity"), output_field=MONEY), Decimal("0.00"))
          )
          .order_by("-revenue")[:limit])

    return Response([{"name": r["product__name"], "units": r["units"], "revenue": r["revenue"]} for r in qs])

class RecentOrders(APIView):
    permission_classes = [IsAdminUser]
    def get(self, request):
        limit = int(request.query_params.get("limit", 8))
        qs = Order.objects.all().order_by("-created")[:limit]
        return Response(OrderListSer(qs, many=True).data)
