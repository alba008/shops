# myshop/my_rest_framework/views_order.py
from decimal import Decimal
from django.db import transaction
from rest_framework.views import APIView
from rest_framework.generics import RetrieveAPIView
from rest_framework.response import Response
from rest_framework import status, serializers

from cart.cart import Cart
from orders.models import Order, OrderItem
from .serializers import OrderCreateSerializer

# Pick only fields that exist on your Order model
def _order_fields(model):
    base = ["id", "first_name", "last_name", "email", "address", "postal_code", "city", "paid"]
    for extra in ("subtotal", "discount", "total", "created", "updated"):
        if hasattr(model, extra):
            base.append(extra)
    return base

class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
    # Explicit fields — avoid errors if names differ
        fields = ["product_id", "price", "quantity", "product", "id"]

class OrderDetailSerializer(serializers.ModelSerializer):
    items = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = _order_fields(Order) + ["items"]

    def get_items(self, obj):
        qs = OrderItem.objects.filter(order=obj)
        data = []
        for it in qs:
            product = it.product
            image_url = ""
            try:
                if hasattr(product, "image") and product.image:
                    # ✅ get absolute or relative URL safely
                    image_url = product.image.url
            except Exception:
                image_url = ""

            data.append({
                "product_id": product.id,
                "name": getattr(product, "name", f"Product {product.id}"),
                "price": str(it.price),
                "quantity": it.quantity,
                "line_total": str(it.get_cost()),
                "product_image": image_url,
            })
        return data

class OrdersView(APIView):
    """
    POST /api/orders/
    Body: { first_name, last_name, email, address, postal_code, city }
    Creates an Order from the current session cart.
    """
    permission_classes = []  # public

    @transaction.atomic
    def post(self, request):
        ser = OrderCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        cart = Cart(request)

        subtotal = cart.get_total_price() if hasattr(cart, "get_total_price") else Decimal("0")
        discount = cart.get_discount() if hasattr(cart, "get_discount") else Decimal("0")
        total = (subtotal - discount).quantize(Decimal("0.01")) if (subtotal or discount) else Decimal("0.00")

        if total <= 0 and len(cart) == 0:
            return Response({"detail": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        order = Order.objects.create(
            first_name = ser.validated_data["first_name"],
            last_name  = ser.validated_data["last_name"],
            email      = ser.validated_data["email"],
            address    = ser.validated_data["address"],
            postal_code= ser.validated_data["postal_code"],
            city       = ser.validated_data["city"],
            paid       = False,
        )

        items_payload = []
        for line in cart:  # Cart.__iter__ yields dicts with 'product','price','quantity'
            product = line["product"]
            unit    = Decimal(line["price"])
            qty     = int(line["quantity"])
            OrderItem.objects.create(order=order, product=product, price=unit, quantity=qty)
            items_payload.append({
                "product_id": product.id,
                "name": product.name,
                "unit_price": str(unit),
                "quantity": qty,
                "line_total": str(unit * qty),
            })

        # Write money fields if they exist on your model
        changed = []
        if hasattr(order, "subtotal"):
            order.subtotal = subtotal; changed.append("subtotal")
        if hasattr(order, "discount"):
            order.discount = discount; changed.append("discount")
        if hasattr(order, "total"):
            order.total = total; changed.append("total")
        if changed:
            order.save(update_fields=changed)

        # Save in session for Stripe fallback
        request.session["last_order_id"] = order.id
        request.session.modified = True

        return Response({
            "id": order.id,
            "subtotal": str(subtotal),
            "discount": str(discount),
            "total": str(total),
            "items": items_payload,
        }, status=status.HTTP_201_CREATED)

class OrderDetailView(RetrieveAPIView):
    """
    GET /api/orders/<pk>/
    """
    queryset = Order.objects.all()
    serializer_class = OrderDetailSerializer
    permission_classes = []
