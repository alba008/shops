# my_rest_framework/views_orders_misc.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from orders.models import Order

class OrderThankYouAPI(APIView):
    permission_classes = []  # AllowAny

    def get(self, request):
        """
        Optional helper endpoint so the FE can call /api/orders/thank-you/?order=ID
        Returns minimal info; real detail is /api/orders/<id>/
        """
        oid = request.GET.get("order") or request.query_params.get("order")
        if not oid:
            # Try session fallback
            oid = request.session.get("last_order_id")

        if not oid:
            return Response({"detail": "No order id."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            order = Order.objects.get(id=oid)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        return Response({
            "order": order.id,
            "paid": order.paid,
            "total": str(getattr(order, "total", "")),
        })
