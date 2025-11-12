# api/accounts/views.py
from django.contrib.auth import get_user_model, authenticate, login, logout
from django.db import IntegrityError
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework.permissions import AllowAny
from rest_framework_simplejwt.authentication import JWTAuthentication

from .serializers import RegisterSerializer, UserSerializer, UserUpdateSerializer

User = get_user_model()


def _nostore_headers():
    return {"Cache-Control": "no-store"}

class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        # normalize (optional)
        data = request.data.copy()
        if "email" in data and isinstance(data["email"], str):
            data["email"] = data["email"].strip().lower()
        if "username" in data and isinstance(data["username"], str):
            data["username"] = data["username"].strip().lower()

        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        payload = {
            "user": UserSerializer(user).data,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        }
        return Response(payload, status=status.HTTP_201_CREATED, headers={"Cache-Control": "no-store"})


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        # accept both username or email
        username = (request.data.get("username") or request.data.get("email") or "").strip().lower()
        password = request.data.get("password")

        # allow login by email
        if "@" in username:
            try:
                from django.contrib.auth import get_user_model
                User = get_user_model()
                obj = User.objects.filter(email__iexact=username).first()
                if obj:
                    username = obj.username
            except Exception:
                pass

        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response({"detail": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED, headers=_nostore_headers())

        # optional session login
        login(request, user)

        # ✅ issue JWT like your RegisterView does
        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "detail": "Login successful",
                "user": UserSerializer(user).data,
                "refresh": str(refresh),
                "access": str(refresh.access_token),
            },
            status=status.HTTP_200_OK,
            headers=_nostore_headers(),
        )


class UserProfileView(generics.RetrieveUpdateAPIView):
    authentication_classes = [JWTAuthentication]              # ← add this
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response


class MeView(APIView):
    authentication_classes = [JWTAuthentication]              # ← add this
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data, headers=_nostore_headers())

    def patch(self, request):
        ser = UserSerializer(request.user, data=request.data, partial=True)
        if ser.is_valid():
            ser.save()
            return Response(ser.data, headers=_nostore_headers())
        return Response(ser.errors, status=400, headers=_nostore_headers())


class UserUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = UserUpdateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response


class LogoutView(APIView):
    # accept from anywhere; don't require CSRF by removing SessionAuthentication
    permission_classes = [AllowAny]
    authentication_classes = []  # ⟵ disables SessionAuthentication (and its CSRF check)

    def post(self, request):
        try:
            # If a session exists, clear it; if not, it's still fine.
            logout(request)
        except Exception:
            pass
        return Response({"detail": "ok"}, headers=_nostore_headers())


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)
        data.update({
            "user": {
                "id": self.user.id,
                "username": self.user.username,
                "email": self.user.email,
            }
        })
        return data


class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer
