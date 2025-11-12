# recommender/management/commands/build_recs.py
from __future__ import annotations

import warnings
from collections import defaultdict
from typing import Dict, Iterable, List, Tuple

from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Count

# Quiet common lib warnings
warnings.filterwarnings("ignore", category=FutureWarning)
warnings.filterwarnings("ignore", category=UserWarning)

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from shop.models import Product
from orders.models import OrderItem  # adjust if your app name/path differs
from recommender.models import ProductSimilarity


# -----------------------
# Helpers
# -----------------------
def _to_text(val) -> str:
    """Coerce any field or related object to a plain string (prefer .name)."""
    if val is None:
        return ""
    name = getattr(val, "name", None)
    if isinstance(name, str):
        return name
    return str(val)


def _tags_to_csv(tags_attr) -> str:
    """
    Handle tags as list/tuple/QuerySet or M2M manager (.all()).
    Returns a CSV of tag names/strings.
    """
    if not tags_attr:
        return ""
    try:
        iterable = tags_attr.all() if hasattr(tags_attr, "all") else tags_attr
    except Exception:
        iterable = []
    names = [str(getattr(t, "name", t)) for t in iterable]
    return ",".join(names)


def product_text(p: Product) -> str:
    """Build a robust text representation for TF-IDF."""
    parts = [
        _to_text(getattr(p, "name", "")),
        _to_text(getattr(p, "description", "")),
        _to_text(getattr(p, "category", "")),  # FK -> Category safely stringified
    ]
    tags_attr = getattr(p, "tags_list", None) or getattr(p, "tags", None)
    parts.append(_tags_to_csv(tags_attr))
    return " ".join(s for s in parts if s).strip()


def build_copurchase_counts(order_items: Iterable[Tuple[int, int]]) -> Dict[Tuple[int, int], int]:
    """
    Build co-purchase counts from (order_id, product_id) pairs.
    Returns dict mapping (pid_a, pid_b) -> count.
    """
    by_order: Dict[int, List[int]] = defaultdict(list)
    for oid, pid in order_items:
        by_order[oid].append(pid)

    co: Dict[Tuple[int, int], int] = defaultdict(int)
    for plist in by_order.values():
        n = len(plist)
        if n < 2:
            continue
        for i in range(n):
            a = plist[i]
            for j in range(i + 1, n):
                b = plist[j]
                if a == b:
                    continue
                co[(a, b)] += 1
                co[(b, a)] += 1
    return co


# -----------------------
# Management command
# -----------------------
class Command(BaseCommand):
    help = "Build product-product similarities and store top-K (TF-IDF + co-purchase blend)."

    def add_arguments(self, parser):
        parser.add_argument("--topk", type=int, default=20, help="Neighbors to store per product.")
        parser.add_argument("--max-features", type=int, default=20000, help="TF-IDF max features.")
        parser.add_argument("--ngram-max", type=int, default=2, help="TF-IDF ngram upper bound (1..N).")
        parser.add_argument("--copurchase-weight", type=float, default=0.30, help="Blend weight for co-purchase (0..1).")
        parser.add_argument("--truncate", type=int, default=0, help="If >0, truncate corpus strings to this many chars.")

    def handle(self, *args, **opts):
        topk: int = opts["topk"]
        max_features: int = opts["max_features"]
        ngram_max: int = opts["ngram_max"]
        w_co: float = opts["copurchase_weight"]
        trunc: int = opts["truncate"]
        verbosity: int = opts.get("verbosity", 1)

        products: List[Product] = list(Product.objects.all())
        if not products:
            if verbosity > 0:
                self.stdout.write(self.style.WARNING("No products found."))
            return

        # --- TF-IDF corpus
        corpus = [product_text(p) for p in products]
        if trunc and trunc > 0:
            corpus = [c[:trunc] for c in corpus]

        vectorizer = TfidfVectorizer(max_features=max_features, ngram_range=(1, ngram_max))
        X = vectorizer.fit_transform(corpus)
        sim = cosine_similarity(X)

        # --- Co-purchase signal
        multi_ids = (
            OrderItem.objects.values("order_id")
            .annotate(n=Count("id"))
            .filter(n__gte=2)
            .values_list("order_id", flat=True)
        )
        order_items = OrderItem.objects.filter(order_id__in=multi_ids).values_list("order_id", "product_id")
        co = build_copurchase_counts(order_items)
        max_co = max(co.values()) if co else 1

        # --- Write results
        with transaction.atomic():
            ProductSimilarity.objects.all().delete()
            bulk: List[ProductSimilarity] = []

            for i, p in enumerate(products):
                row = sim[i]
                scored: List[Tuple[int, float]] = []
                for j, q in enumerate(products):
                    if i == j:
                        continue
                    s = float(row[j])
                    c = co.get((p.id, q.id), 0)
                    if c and w_co > 0 and max_co > 0:
                        s += w_co * (c / max_co)
                    scored.append((q.id, s))

                scored.sort(key=lambda t: t[1], reverse=True)
                for pid, sc in scored[:topk]:
                    bulk.append(ProductSimilarity(base=p, other_id=pid, score=sc))

            ProductSimilarity.objects.bulk_create(bulk, batch_size=2000)

        if verbosity > 0:
            self.stdout.write(self.style.SUCCESS(f"Built similarities for {len(products)} products (topK={topk})."))
