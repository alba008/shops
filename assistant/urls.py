# assistant/urls.py
from django.urls import path
from .views import shop_assistant_view

urlpatterns = [
    path("shop-assistant/", shop_assistant_view, name="shop-assistant"),
]
