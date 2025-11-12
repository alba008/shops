# accounts/api_register.py
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from .emails import send_welcome

@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    data = request.data or {}
    email = data.get("email")
    password = data.get("password")
    username = data.get("username") or email.split("@")[0]
    User = get_user_model()
    user = User.objects.create_user(username=username, email=email, password=password)
    send_welcome(user)  # <-- guaranteed send
    return Response({"ok": True, "id": user.id})
