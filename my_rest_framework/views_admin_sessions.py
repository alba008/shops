# myshop/my_rest_framework/views_admin_sessions.py
from django.contrib.sessions.models import Session
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework import status

User = get_user_model()

def _session_row(s: Session):
    data = s.get_decoded() or {}
    uid = data.get("_auth_user_id")
    user = None
    if uid:
        try:
            u = User.objects.get(id=uid)
            user = {
                "id": u.id, "email": u.email,
                "first_name": getattr(u, "first_name", ""),
                "last_name": getattr(u, "last_name", ""),
                "is_staff": u.is_staff,
            }
        except User.DoesNotExist:
            pass
    return {
        "key": s.session_key,
        "expire_date": s.expire_date,
        "user": user,
        "last_order_id": data.get("last_order_id"),
        "cart_count": data.get("cart_count"),
    }

class AdminSessionListView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request):
        now = timezone.now()
        sessions = Session.objects.filter(expire_date__gt=now).order_by("-expire_date")[:500]
        return Response([_session_row(s) for s in sessions])

class AdminSessionDeleteView(APIView):
    permission_classes = [IsAdminUser]

    def delete(self, request, key):
        try:
            Session.objects.get(session_key=key).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Session.DoesNotExist:
            return Response({"detail": "Not found"}, status=status.HTTP_404_NOT_FOUND)
