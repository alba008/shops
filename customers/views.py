# customers/views.py
from django.db.models import Count, Max
from rest_framework import viewsets, permissions
from .models import Customer
from .serializers import CustomerSer

class CustomerViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = CustomerSer

    def get_queryset(self):
        # annotate last_order_at and total_orders if you have Order model with FK customer
        qs = Customer.objects.all()
        try:
            from orders.models import Order
            return qs.annotate(
                total_orders=Count("order"),
                last_order_at=Max("order__created"),
            ).order_by("-created")
        except Exception:
            return qs.order_by("-created")
