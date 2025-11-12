from django.urls import path
from .views import recommend_products

urlpatterns = [
    path('', recommend_products),
]
