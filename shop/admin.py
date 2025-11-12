from django.contrib import admin
from .models import (
    Category, SubCategory, Product, ProductImage, Banner,
    GalleryImage, Color, Size
)
from .models import MarketingImage


# Register your models here.
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug','parent',]
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name']
    list_filter = ['parent']
    ordering = ['name']



@admin.register(SubCategory)
class SubCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug', 'category',]
    prepopulated_fields = {'slug': ('name',)}
    search_fields = ['name', 'category__name']
    list_filter = ['category',]
    ordering = ['name']


# ------------ Product Images Inline ------------
class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = [
        'name',
        'slug',
        'price',
        'available',
        'created',
        'updated'
    ]
    list_filter = ['available', 'category', 'colors',  'created','updated']
    list_editable = ['price', 'available']
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline]
    filter_horizontal = ['colors', 'sizes']
    fieldsets = (
        (None, {
            'fields': ('name', 'slug', 'category', 'brand', 'description', 'product_link')
        }),
        ('Media & Gallery', {
            'fields': ('image',),
        }),
        ('Attributes', {
            'fields': ('price', 'available', 'rating', 'pattern', 'material', 'care_instructions')
        }),
        ('Options', {
            'fields': ('colors', 'sizes')
        }),
    )

    @admin.register(Banner)
    class BannerAdmin(admin.ModelAdmin):
      list_display = ('title', 'image')


admin.site.register(GalleryImage)



# ------------ Product Image Admin ------------
@admin.register(ProductImage)
class ProductImageAdmin(admin.ModelAdmin):
    list_display = ['product', 'alt_text']
    search_fields = ['product__name', 'alt_text']


# ------------ Color Admin ------------
@admin.register(Color)
class ColorAdmin(admin.ModelAdmin):
    list_display = ['name', 'hex']
    search_fields = ['name']

# ------------ Size Admin ------------
@admin.register(Size)
class SizeAdmin(admin.ModelAdmin):
    list_display = ['label']
    search_fields = ['label']



@admin.register(MarketingImage)
class MarketingImageAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "section", "is_active", "ordering", "created")
    list_filter = ("section", "is_active")
    search_fields = ("title", "subtitle")
    ordering = ("ordering", "-id")