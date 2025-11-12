# recommendation/utils.py

from shop.models import Product
from .models import UserInteraction
from django.db.models import Count

def get_recommendations_for_user(user_id, limit=5):
    # Step 1: Get product IDs user has already interacted with
    seen_product_ids = UserInteraction.objects.filter(
        user_id=user_id
    ).values_list('product_id', flat=True)

    # Step 2: Find most-viewed products not seen by this user
    recommendations = (
        UserInteraction.objects
        .exclude(product_id__in=seen_product_ids)
        .values('product_id')
        .annotate(total=Count('id'))
        .order_by('-total')[:limit]
    )

    product_ids = [r['product_id'] for r in recommendations]
    return Product.objects.filter(id__in=product_ids)
