from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.shortcuts import get_object_or_404
from shop.models import Product
from .cart import Cart
from .serializers import CartSerializer, CartItemAddSerializer

class CartDetailView(APIView):
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get(self, request):
        cart = Cart(request)
        data = {
            "items": [
                {
                    "product_id": item["product"].id,
                    "title": item["product"].title,
                    "quantity": item["quantity"],
                    "price": str(item["price"]),
                    "total_price": str(item["total_price"]),
                }
                for item in cart
            ],
            "subtotal": str(cart.get_total_price()),
            "total_after_discount": str(cart.get_total_price_after_discount()),
        }
        return Response(data, status=status.HTTP_200_OK)


class CartAddView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CartItemAddSerializer(data=request.data)
        if serializer.is_valid():
            product_id = serializer.validated_data["product_id"]
            quantity = serializer.validated_data.get("quantity", 1)
            product = get_object_or_404(Product, id=product_id)

            cart = Cart(request)
            cart.add(product=product, quantity=quantity)
            return Response(
                {"message": "Added to cart", "product_id": product_id, "quantity": quantity},
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CartRemoveView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = CartItemAddSerializer(data=request.data)
        if serializer.is_valid():
            product_id = serializer.validated_data["product_id"]
            product = get_object_or_404(Product, id=product_id)
            cart = Cart(request)
            cart.remove(product)
            return Response({"message": "Removed from cart"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CartDetailView(APIView):
    """
    Returns all items in the current user's session cart.
    """
    def get(self, request):
        cart = Cart(request)
        data = []

        for item in cart:
            product = item.get('product')
            data.append({
                'id': product.id if product else None,
                'name': product.title if product else '',
                'price': str(item['price']),
                'quantity': item['quantity'],
                'total_price': str(item['total_price']),
            })
        return Response({'cart': data, 'total': str(cart.get_total_price())}, status=status.HTTP_200_OK)
