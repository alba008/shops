# myshop/accounts/urls.py
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    RegisterView,
    MeView,                 # current user (GET/PATCH) — returns UserSerializer (with is_staff)
    UserProfileView,        # edit/read core User fields (if you still want this separate)
    UserUpdateView,         # optional alias to update user (you can keep or drop)
    LogoutView,
    MyTokenObtainPairView,  # login that returns {access, refresh, user:{...}}
)
from .views_profile import ProfileView, PasswordChangeView
from .api_password_reset import password_reset_request, password_reset_confirm

urlpatterns = [
    # Auth
    path("register/", RegisterView.as_view(), name="register"),
    path("login/",    MyTokenObtainPairView.as_view(), name="login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("logout/",   LogoutView.as_view(), name="logout"),

    # Current user (JWT-protected)
    path("me/",       MeView.as_view(), name="me"),

    # User model fields (username, first_name, last_name, etc.)
    # Keep exactly one route for this; do NOT duplicate the path.
    path("user/",     UserProfileView.as_view(), name="user-profile"),     # <- renamed from "profile/"

    # Extended Profile model (phone, avatar, etc.)
    path("profile/",  ProfileView.as_view(), name="profile-detail"),       # <- keeps /profile/ for Profile model
    path("password/", PasswordChangeView.as_view(), name="password-change"),

    # Password reset (public)
    path("password-reset/",           password_reset_request,  name="password-reset"),
    path("password-reset/confirm/",   password_reset_confirm,  name="password-reset-confirm"),
]
