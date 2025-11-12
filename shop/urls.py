from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from .views import (
    ProductViewSet, CategoryViewSet, SubCategoryViewSet,
    ColorViewSet, SizeViewSet, ProductImageViewSet,
    BannerViewSet, GalleryImageViewSet, MarketingImageViewSet,
    gallery_view
)
from django.views.decorators.csrf import csrf_exempt
from graphene_django.views import GraphQLView
from products.views import ProductViewSet
from customers.views import CustomerViewSet
from inventory.views import StockLedgerViewSet


router = DefaultRouter()
router.register(r'products', ProductViewSet)
router.register(r'categories', CategoryViewSet)
router.register(r'subcategories', SubCategoryViewSet)
router.register(r'colors', ColorViewSet)
router.register(r'sizes', SizeViewSet)
router.register(r'product-images', ProductImageViewSet)
router.register(r'banners', BannerViewSet)
router.register(r'gallery-images', GalleryImageViewSet)
router.register(r'marketing-images', MarketingImageViewSet)
router.register(r'admin/products', ProductViewSet, basename='admin-products')
router.register(r'admin/customers', CustomerViewSet, basename='admin-customers')
router.register(r'admin/stock', StockLedgerViewSet, basename='admin-stock')


app_name = 'shop'

urlpatterns = [
    path('', include(router.urls)),  # ✅ Router URLs first

    path('gallery/', gallery_view, name='gallery'),

    path('products/', views.product_list, name='product_list'),
    path('products/<slug:category_slug>/', views.product_list, name='product_list_by_category'),
    path('products/<int:id>/<slug:slug>/', views.product_detail, name='product_detail'),

    path('shop/', views.product_lists, name='product_lists'),
    path('shop/<slug:category_slug>/', views.product_lists, name='product_lists_by_category'),
    path("graphql", csrf_exempt(GraphQLView.as_view(graphiql=True))),

]
