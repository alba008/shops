from django.db import models
from shop.models import Product 

class UserInteraction(models.Model):
    ACTIONS = [
        ('view', 'View'),
        ('click', 'Click'),
        ('purchase', 'Purchase'),
    ]
    user_id = models.CharField(max_length=50)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    action = models.CharField(max_length=10, choices=ACTIONS)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user_id} - {self.action} - {self.product.name}"


