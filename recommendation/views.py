# recommendation/views.py

from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status

def get_recommendations_for_user(username):
    from shop.models import Product
    from orders.models import OrderItem
    from django.contrib.auth import get_user_model
    from django.db.models import Count

    User = get_user_model()

    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        # fallback: return 3 random products if user not found
        return Product.objects.all().order_by('?')[:3]

    user_product_ids = OrderItem.objects.filter(order__user=user).values_list('product_id', flat=True)

    similar_users = OrderItem.objects.filter(
        product_id__in=user_product_ids
    ).exclude(order__user=user).values_list('order__user', flat=True)

    recommended_product_data = (
        OrderItem.objects
        .filter(order__user__in=similar_users)
        .exclude(product_id__in=user_product_ids)
        .values('product_id')
        .annotate(freq=Count('product_id'))
        .order_by('-freq')[:5]
    )

    product_ids = [item['product_id'] for item in recommended_product_data]
    return Product.objects.filter(id__in=product_ids)

@api_view(['POST'])
def recommend_products(request):
    print("Request data:", request.data)
    username = request.data.get('user_id')  # it's actually a username now

    if not username:
        return Response({"error": "user_id is required"}, status=status.HTTP_400_BAD_REQUEST)

    recommendations = get_recommendations_for_user(username)
    data = [{"id": p.id, "name": p.name, "price": p.price} for p in recommendations]
    return Response(data)
