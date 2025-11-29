# myshop/urls.py
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.conf.urls.i18n import i18n_patterns
from django.views.decorators.csrf import csrf_exempt

from graphene_django.views import GraphQLView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import csrf_view
from shop import stripe_views
from cart import views as cart_views


# Public (accounts/me = authenticated user, not staff-only)
from accounts import api as accounts_api

# Admin APIs (staff-only)
from accounts import views_admin as accounts_admin
from orders import views_admin as orders_admin
from shop import views_admin as shop_admin
from support import views_admin as support_admin

# Public order views (detail + items + last)
from orders.views_public import (
    order_detail_public,
    order_items_public,
    last_order,
    my_orders,  # 👈 new

)

# Cart API helper (hard clear after checkout)
from cart.views import empty_cart

# ---------------------------------------
# 1) Non-localized API routes (no /en/)
# ---------------------------------------
api_patterns = [
    # ---------- Public orders (EXPLICIT, must be FIRST) ----------
    path("api/orders/last/",           last_order,           name="orders-last"),
    path("api/orders/my/",             my_orders,            name="orders-my"),   # 👈 new
    path("api/orders/<int:pk>/",       order_detail_public,  name="order-detail-public"),
    path("api/orders/<int:pk>/items/", order_items_public,   name="order-items-public"),

    # ---------- Cart helpers ----------
    path("api/cart/empty/", empty_cart, name="cart-empty"),

    # ---------- Core app APIs ----------
    path("api/", include("my_rest_framework.urls")),
    path("api/", include("shop.urls")),                # products, banners, marketing-images, etc.
    path("api/", include("support.urls")),             # enquiries (router-based public/admin as defined)
    path("api/recommend/", include("recommendation.urls")),

    # ---------- Auth & session ----------
    path("api/accounts/", include("accounts.urls")),   # register/login/logout etc.
    path("api/csrf/", csrf_view),

    # ---------- Stripe ----------
    path("api/checkout/stripe-session/", stripe_views.create_stripe_session, name="checkout-stripe-session"),
    path("api/stripe/webhook/",          stripe_views.stripe_webhook,        name="stripe-webhook"),

    # ---------- SimpleJWT ----------
    path("api/token/",         TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(),    name="token_refresh"),

    # ---------- Public “me” (any authenticated user) ----------
    path("api/accounts/me/", accounts_api.me, name="accounts-me"),

    # ---------- Admin (staff-only) ----------
    # Accounts
    path("api/admin/me/", accounts_admin.me, name="admin-me"),

    # Dashboard stats
    path("api/admin/stats/",     orders_admin.stats,     name="admin-stats"),
    path("api/admin/sales_7d/",  orders_admin.sales_7d,  name="admin-sales-7d"),
    path("api/admin/sales_30d/", orders_admin.sales_30d, name="admin-sales-30d"),

    # Orders
    path("api/admin/recent_orders/",             orders_admin.RecentOrders.as_view(), name="admin-recent-orders"),
    path("api/admin/orders/",                    orders_admin.OrderList.as_view(),    name="admin-orders"),
    path("api/admin/orders/<int:pk>/",           orders_admin.OrderDetail.as_view(),  name="admin-order-detail"),
    path("api/admin/orders/<int:pk>/mark_paid/", orders_admin.mark_paid,              name="admin-order-mark-paid"),

    # Products
    path("api/admin/top_products/", orders_admin.top_products, name="admin-top-products"),
    path("api/admin/low_stock/",    shop_admin.low_stock,      name="admin-low-stock"),
    path("api/admin/products/",     shop_admin.products,       name="admin-products"),

    # Enquiries
    path("api/admin/enquiries/summary/", support_admin.enquiry_summary, name="admin-enquiry-summary"),
]

# Start with API + site root
urlpatterns = api_patterns

# ---------------------------------------
# 2) Localized (Django admin, site sections)
# ---------------------------------------
urlpatterns += i18n_patterns(
    path("admin/", admin.site.urls),
    path("cart/", include(("cart.urls", "cart"), namespace="cart")),
    path("orders/", include(("orders.urls", "orders"), namespace="orders")),
    path("payment/", include(("payment.urls", "payment"), namespace="payment")),
    path("coupons/", include(("coupons.urls", "coupons"), namespace="coupons")),
    path("rosetta/", include("rosetta.urls")),
    path("accounts/", include("accounts.urls")),
    path("graphql", csrf_exempt(GraphQLView.as_view(graphiql=True))),
)

# Media (dev)
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
