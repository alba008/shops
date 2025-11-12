# recommender/schema.py
from __future__ import annotations
import math
import logging
import graphene
from graphene_django import DjangoObjectType
from django.db.models import Count
from shop.models import Product
from orders.models import OrderItem
from recommender.models import ProductSimilarity

logger = logging.getLogger(__name__)

# ---- Optional: only import LLM if configured, and guard at call site
try:
    from recommender.llm import rerank_with_ollama
except Exception as e:
    logger.warning("LLM rerank unavailable: %s", e)
    rerank_with_ollama = None


class ProductType(DjangoObjectType):
    class Meta:
        model = Product
        # adapt to your fields
        fields = ("id", "name", "price", "image")


class Query(graphene.ObjectType):
    recommended_products = graphene.List(
        ProductType,
        product_id=graphene.ID(required=True),
        first=graphene.Int(default_value=12),
        budget=graphene.Float(),                  # optional
        exclude_ids=graphene.List(graphene.ID),   # optional
    )

    def resolve_recommended_products(
        self,
        info,
        product_id,
        first=12,
        budget=None,
        exclude_ids=None,
    ):
        # ---- normalize inputs safely ----
        try:
            anchor_id = int(product_id)
        except Exception:
            logger.exception("Bad product_id: %r", product_id)
            return []

        try:
            first = int(first or 12)
            first = max(1, min(first, 50))
        except Exception:
            first = 12

        ex_ids = set()
        for x in exclude_ids or []:
            try:
                ex_ids.add(int(x))
            except Exception:
                continue

        has_budget = budget is not None and str(budget) != "" and not (isinstance(budget, float) and math.isnan(budget))
        max_price = float(budget) if has_budget else None

        # ---- try anchor product (for category fallback) ----
        anchor = Product.objects.filter(id=anchor_id).first()

        # ---- 1) precomputed similarities ----
        sims = list(
            ProductSimilarity.objects
            .filter(base_id=anchor_id)
            .order_by("-score")
            .values_list("other_id", flat=True)[: max(first, 30)]
        )

        # ---- 2) fallback candidates ----
        if not sims:
            same_cat_ids = []
            if anchor and getattr(anchor, "category_id", None):
                same_cat_ids = list(
                    Product.objects
                    .filter(category_id=anchor.category_id)
                    .exclude(id=anchor_id)
                    .values_list("id", flat=True)[:60]
                )

            popular_ids = list(
                OrderItem.objects
                .values("product_id")
                .annotate(n=Count("id"))
                .order_by("-n")
                .values_list("product_id", flat=True)[:60]
            )

            # combine: prefer same category, then popular (unique, drop anchor)
            seen = {anchor_id}
            sims = []
            for pid in same_cat_ids + popular_ids:
                if pid in seen:
                    continue
                seen.add(pid)
                sims.append(pid)

        # no candidates at all → site-wide recent/popular as last resort
        if not sims:
            sims = list(
                Product.objects
                .exclude(id=anchor_id)
                .order_by("-id")
                .values_list("id", flat=True)[: max(first, 30)]
            )

        # ---- apply exclude + budget filters safely ----
        if ex_ids:
            sims = [pid for pid in sims if pid not in ex_ids]

        if has_budget:
            prices = dict(Product.objects.filter(id__in=sims).values_list("id", "price"))
            sims = [pid for pid in sims if pid in prices and prices[pid] is not None and float(prices[pid]) <= max_price]

        # still nothing? bail early
        if not sims:
            return []

        # ---- optional LLM rerank with guard ----
        ranked_ids = []
        if rerank_with_ollama:
            try:
                def lookup(pid): return Product.objects.get(id=pid)
                context = {
                    "intent": "similar",
                    "anchor_product_id": anchor_id,
                    "budget": max_price,
                    "recent_product_ids": [],
                }
                ranked_ids = rerank_with_ollama(context, sims, lookup) or []
            except Exception:
                logger.exception("LLM rerank failed; using baseline order.")
                ranked_ids = []

        ids_final = (ranked_ids or sims)[:first]

        # ---- hydrate & preserve order ----
        products = list(Product.objects.filter(id__in=ids_final))
        idx = {pid: i for i, pid in enumerate(ids_final)}
        products.sort(key=lambda p: idx.get(p.id, 10_000))
        return products


schema = graphene.Schema(query=Query)
