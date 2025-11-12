# recommender/views.py
from __future__ import annotations

from collections import defaultdict
from typing import List

from django.db.models import Count
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from shop.models import Product
from orders.models import OrderItem
from .models import ProductSimilarity
from .serializers import ProductCardSerializer
from .llm import rerank_with_ollama


class ProductRecommendations(APIView):
    """
    GET /api/recommendations/product/<product_id>/
    Baseline: top ProductSimilarity rows for the anchor product.
    Then rerank with Ollama (Llama 3) and return top 12.
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, product_id: int):
        # 1) Candidate generation (baseline)
        sims: List[int] = list(
            ProductSimilarity.objects
            .filter(base_id=product_id)
            .order_by('-score')
            .values_list('other_id', flat=True)[:30]
        )

        # Fallback to popular if no similarity rows exist
        if not sims:
            popular = (
                OrderItem.objects.values('product_id')
                .annotate(n=Count('id'))
                .order_by('-n')[:30]
            )
            sims = [p['product_id'] for p in popular]

        def lookup(pid: int) -> Product:
            return Product.objects.get(id=pid)

        # 2) LLM rerank
        context = {"intent": "similar", "anchor_product_id": int(product_id)}
        ranked_ids = rerank_with_ollama(context, sims, lookup)

        # 3) Fetch and preserve order (limit to 12)
        top_ids = ranked_ids[:12] if ranked_ids else []
        products = list(Product.objects.filter(id__in=top_ids))
        products.sort(key=lambda p: top_ids.index(p.id) if p.id in top_ids else 1_000_000)

        data = ProductCardSerializer(products, many=True).data
        return Response({"source": "llama3_rerank", "items": data})


class UserRecommendations(APIView):
    """
    GET /api/recommendations/user/<user_id>/
    Uses the authenticated user's recent purchases to form candidates,
    then reranks with Ollama and returns top 12.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, user_id=None):
        user = request.user

        # 1) Recent interactions → product IDs
        last_items = (
            OrderItem.objects
            .filter(order__user=user)
            .values('product_id')
            .annotate(n=Count('id'))
            .order_by('-n')[:5]
        )
        pids = [r['product_id'] for r in last_items]

        # Candidate generation
        if not pids:
            # Cold-start: popular items
            popular = (
                OrderItem.objects.values('product_id')
                .annotate(n=Count('id'))
                .order_by('-n')[:30]
            )
            sims = [p['product_id'] for p in popular]
        else:
            # Merge similar lists across last seen/bought products
            scores = defaultdict(float)
            for pid in pids:
                for s in (
                    ProductSimilarity.objects
                    .filter(base_id=pid)
                    .order_by('-score')[:30]
                ):
                    scores[s.other_id] += s.score
            # Remove already bought/seen
            for pid in pids:
                scores.pop(pid, None)
            sims = [pid for pid, _ in sorted(scores.items(), key=lambda x: x[1], reverse=True)[:30]]

        def lookup(pid: int) -> Product:
            return Product.objects.get(id=pid)

        # 2) LLM rerank
        context = {
            "intent": "personalized",
            "recent_product_ids": pids,
        }
        ranked_ids = rerank_with_ollama(context, sims, lookup)

        # 3) Fetch and preserve order (limit to 12)
        top_ids = ranked_ids[:12] if ranked_ids else []
        products = list(Product.objects.filter(id__in=top_ids))
        products.sort(key=lambda p: top_ids.index(p.id) if p.id in top_ids else 1_000_000)

        data = ProductCardSerializer(products, many=True).data
        return Response({"source": "llama3_rerank", "items": data})
