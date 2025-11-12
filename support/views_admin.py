# myshop/support/views_admin.py
from django.db.models import Count
from rest_framework.decorators import api_view, permission_classes, authentication_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import Enquiry
from .serializers import EnquirySerializer  # see below

@api_view(["GET"])
@authentication_classes([JWTAuthentication])    # ← accept Bearer tokens
@permission_classes([IsAdminUser])              # ← staff/superuser only
def enquiry_summary(request):
    """
    GET /api/support/admin/enquiries/summary/
    Returns counts of enquiries by status. Requires staff/superuser with JWT.
    """
    agg = Enquiry.objects.values("status").annotate(c=Count("id"))
    out = {"open": 0, "pending": 0, "resolved": 0}
    for row in agg:
        s = (row["status"] or "").lower()
        if s in out:
            out[s] = row["c"]
    return Response(out)


@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAdminUser])
def enquiry_list(request):
    """
    GET /api/support/admin/enquiries/
    Return all enquiries (or filter later). Requires staff/superuser with JWT.
    """
    qs = Enquiry.objects.all().order_by("-created_at")
    data = EnquirySerializer(qs, many=True).data
    return Response({"results": data}, status=status.HTTP_200_OK)


@api_view(["GET"])
@authentication_classes([JWTAuthentication])
@permission_classes([IsAdminUser])
def admin_ping(request):
    """
    GET /api/support/admin/ping/
    Quick health/auth check used by the staff UI.
    """
    u = request.user
    return Response(
        {
            "ok": True,
            "user": {
                "id": u.id,
                "username": u.username,
                "email": getattr(u, "email", ""),
                "is_staff": bool(u.is_staff),
                "is_superuser": bool(u.is_superuser),
            },
        },
        status=200,
    )
