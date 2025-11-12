from django.shortcuts import get_object_or_404, render
from .models import Banner
from cart.forms import CartAddProductForm
from .models import Category, Product, SubCategory
from .recommender import Recommender
from .models import GalleryImage
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from .models import (
    Product, Category, SubCategory, Color, Size,
    Banner, GalleryImage, ProductImage,  MarketingImage, 
)
from .serializers import (
    ProductSerializer, CategorySerializer, SubCategorySerializer,
    ColorSerializer, SizeSerializer, BannerSerializer,
    GalleryImageSerializer, ProductImageSerializer,  MarketingImageSerializer,
)
from .models import MarketingImage
from shop.filters import ProductImageFilter, GalleryImageFilter  # ✅ import

from rest_framework.permissions import AllowAny

from django.http import JsonResponse
from django.views.decorators.csrf import ensure_csrf_cookie

@ensure_csrf_cookie
def csrf_view(request):
    # Just sets the csrftoken cookie; response body isn't important
    return JsonResponse({"detail": "ok"})



def product_list(request, category_slug=None,  subcategory_slug=None):
    category = None
    subcategory = None
    categories = Category.objects.filter(parent__isnull=True)  # Fetch root categories
    products = Product.objects.filter(available=True)
    banners = Banner.objects.all()  # Fetch banners
    gallery_images = GalleryImage.objects.all()
    

    # Search functionality
    query = request.GET.get('q')
    if query:
        products = products.filter(name__icontains=query)  # Search by product name

    if category_slug:
       category = get_object_or_404(Category, slug=category_slug)
       products = Product.objects.filter(category=category)


    return render(
        request,
        'shop/product/list.html',
        {
            'category': category,
            'categories': categories,
            'products': products,
            'banners': banners,  # Pass banners to the template
            'gallery_images': gallery_images,

        },
    )



def product_detail(request, id, slug):
    product = get_object_or_404(
        Product, id=id, slug=slug, available=True
    )
    cart_product_form = CartAddProductForm()
    r = Recommender()
    recommended_products = r.suggest_products_for([product], 4)
    return render(
        request,
        'shop/product/detail.html',
        {
            'product': product,
            'cart_product_form': cart_product_form,
            'recommended_products': recommended_products,
        },
    )

def product_lists(request, category_slug=None):
    category = None
    categories = Category.objects.all()
    products = Product.objects.filter(available=True)

    if category_slug:
        category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=category)

    return render(request, 'shop/product/list.html', {
        'category': category,
        'categories': categories,
        'products': products
    })



def gallery_view(request):
    gallery_images = GalleryImage.objects.all()
    return render(request, 'shop/list.html', {'gallery_images': gallery_images})


class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer

class SubCategoryViewSet(viewsets.ModelViewSet):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer

class ColorViewSet(viewsets.ModelViewSet):
    queryset = Color.objects.all()
    serializer_class = ColorSerializer

class SizeViewSet(viewsets.ModelViewSet):
    queryset = Size.objects.all()
    serializer_class = SizeSerializer

class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    serializer_class = ProductSerializer
    permission_classes = [AllowAny]
    ordering_fields = ["id", "name", "created"]

class ProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    filterset_class = ProductImageFilter
    permission_classes = [AllowAny]
    ordering_fields = ["id", "pk"]

class BannerViewSet(viewsets.ModelViewSet):
    queryset = Banner.objects.all()
    serializer_class = BannerSerializer

class GalleryImageViewSet(viewsets.ModelViewSet):
    queryset = GalleryImage.objects.all()
    serializer_class = GalleryImageSerializer
    filterset_class = GalleryImageFilter
    permission_classes = [AllowAny]
    ordering_fields = ["id", "uploaded_at"]

class MarketingImageViewSet(viewsets.ModelViewSet):
    queryset = MarketingImage.objects.all()
    serializer_class = MarketingImageSerializer

    def get_queryset(self):
        _ = self.request.query_params.get("product")  # read & ignore
        return super().get_queryset()