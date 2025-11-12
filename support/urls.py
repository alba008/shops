# support/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import EnquiryViewSet

router = DefaultRouter()
router.register(r"enquiries", EnquiryViewSet, basename="enquiry")  # /api/enquiries/

urlpatterns = [
    path("", include(router.urls)),
]
