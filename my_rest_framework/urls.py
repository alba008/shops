# myshop/my_rest_framework/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views_session import SessionView, SessionAttachOrderView
from .views_admin_sessions import AdminSessionListView, AdminSessionDeleteView
from .views_session import session_state
from .views_checkout import CreateCheckoutSessionView, FinalizeCheckoutView


from .views_products import (
    ProductListAPIView,
    ProductDetailAPIView,
    CategoryViewSet,
    SubCategoryViewSet,
)
from .views_cart import CartView, CartItemView, CouponView, CartCountView
from .views_content import MarketingImageViewSet

# ✅ import from framework (this app), not orders.views
from .views_orders import OrdersView, OrderDetailView

# Stripe endpoint (function view that builds a Checkout Session)
from shop import stripe_views  # uses shop/stripe_views.py

from rest_framework.authtoken.views import obtain_auth_token
from rest_framework_simplejwt.views import (
    TokenObtainPairView, TokenRefreshView, TokenVerifyView,
)
from .views_accounts import AccountsMeView
from .views_orders_misc import OrderThankYouAPI



router = DefaultRouter()
router.register(r"categories", CategoryViewSet, basename="category")
router.register(r"subcategories", SubCategoryViewSet, basename="subcategory")
router.register(r"marketing-images", MarketingImageViewSet, basename="marketingimage")

urlpatterns = [

    path("accounts/user/", AccountsMeView.as_view(), name="accounts-me"),
    path("orders/thank-you/", OrderThankYouAPI.as_view(), name="orders-thank-you"),

    path("accounts/session/", SessionView.as_view(), name="api-session"),
    path("accounts/session/attach-order/", SessionAttachOrderView.as_view(), name="api-session-attach-order"),

    path("session/", session_state, name="session-state"),

    # admin / staff controls
    path("admin/sessions/", AdminSessionListView.as_view(), name="api-admin-sessions"),
    path("admin/sessions/<str:key>/", AdminSessionDeleteView.as_view(), name="api-admin-session-delete"),

    # ---------- Products ----------
    path("products/", ProductListAPIView.as_view(), name="product-list"),
    path("products/<int:pk>/", ProductDetailAPIView.as_view(), name="product-detail"),

    # ---------- Cart (session-based) ----------
    path("cart/", CartView.as_view(), name="api-cart"),
    path("cart/item/", CartItemView.as_view(), name="api-cart-item"),
    path("cart/coupon/", CouponView.as_view(), name="api-cart-coupon"),
    path("cart/count/", CartCountView.as_view(), name="api-cart-count"),

    # ---------- Orders (framework-owned engine) ----------
    path("orders/", OrdersView.as_view(), name="orders"),
    path("orders/<int:pk>/", OrderDetailView.as_view(), name="order-detail"),

    # ---------- Checkout / Stripe ----------
    path("checkout/stripe-session/", stripe_views.create_stripe_session, name="checkout-stripe-session"),
    # Back-compat for any code calling /checkout/init/
    path("checkout/init/", stripe_views.create_stripe_session, name="checkout-init"),

    path("checkout/create/", CreateCheckoutSessionView.as_view(), name="checkout-create"),
    path("checkout/finalize/", FinalizeCheckoutView.as_view(), name="checkout-finalize"),


    # ---------- Auth ----------
    path("auth-token/", obtain_auth_token, name="api_token_auth"),
    path("auth/jwt/create/",  TokenObtainPairView.as_view(), name="jwt-create"),
    path("auth/jwt/refresh/", TokenRefreshView.as_view(),    name="jwt-refresh"),
    path("auth/jwt/verify/",  TokenVerifyView.as_view(),     name="jwt-verify"),

    # ---------- Routers (categories, subcategories, marketing images) ----------
    path("", include(router.urls)),
]
