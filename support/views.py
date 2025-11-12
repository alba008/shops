from rest_framework import viewsets, permissions, filters
from rest_framework.pagination import PageNumberPagination
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import Enquiry
from .serializers import EnquirySerializer

class SmallPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = "page_size"
    max_page_size = 200

class EnquiryViewSet(viewsets.ModelViewSet):
    """
    Admin-only CRUD for customer enquiries.
    NOTE: Router is mounted at /api/support/enquiries/ (see support/urls.py)
      GET  /api/support/enquiries/           -> list (staff-only)
      POST /api/support/enquiries/           -> create (public)
      GET  /api/support/enquiries/{id}/      -> retrieve (staff-only)
      PATCH/PUT/DELETE ...                   -> manage (staff-only)
    """
    queryset = Enquiry.objects.all().order_by("-id")
    serializer_class = EnquirySerializer
    pagination_class = SmallPagination
    authentication_classes = [JWTAuthentication]              # ← ensure Bearer works
    permission_classes = [permissions.IsAdminUser]            # default for non-POST

    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ["email", "subject", "message", "status"]
    ordering_fields = ["id", "created_at", "status"]
    ordering = ["-id"]

    def get_permissions(self):
        # Public can create; everything else requires staff/superuser
        if self.action == "create":
            return [permissions.AllowAny()]
        return [permissions.IsAdminUser()]
