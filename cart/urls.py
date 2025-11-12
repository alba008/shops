from django.urls import path
from . import views
from . import api_views

app_name = 'cart'
urlpatterns = [
    path('', views.cart_detail, name='cart_detail'),
    path('add/<int:product_id>/', views.cart_add, name='cart_add'),
    path(
        'remove/<int:product_id>/',
        views.cart_remove,
        name='cart_remove'
    ),
        path("", api_views.CartDetailView.as_view(), name="cart-detail"),
    path("add/", api_views.CartAddView.as_view(), name="cart-add"),
    path("remove/", api_views.CartRemoveView.as_view(), name="cart-remove"),

]

