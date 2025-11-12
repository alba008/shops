# accounts/views_admin.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response

@api_view(["GET"])
@permission_classes([IsAdminUser])
def me(request):
    u = request.user
    return Response({
        "id": u.id,
        "email": getattr(u, "email", None),
        "is_staff": bool(getattr(u, "is_staff", False)),
        "is_superuser": bool(getattr(u, "is_superuser", False)),
    })
