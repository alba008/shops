from django.db import models
from django.conf import settings
from shop.models import Product


class ProductSimilarity(models.Model):
    base = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sim_base')
    other = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='sim_other')
    score = models.FloatField(default=0.0)


class Meta:
    unique_together = ("base", "other")
    indexes = [
    models.Index(fields=["base", "score"]),
    ]


class UserRecommendation(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    score = models.FloatField(default=0.0)


class Meta:
    unique_together = ("user", "product")
    indexes = [models.Index(fields=["user", "score"])]