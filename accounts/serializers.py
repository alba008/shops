# myshop/accounts/serializers.py
from django.contrib.auth import get_user_model, password_validation
from rest_framework import serializers
from .models import Profile

User = get_user_model()

# ---------- Helpers ----------
def _safe_permissions(user):
    try:
        return sorted(list(user.get_all_permissions()))
    except Exception:
        return []

# ---------- READ/UPDATE CURRENT USER ----------
class UserSerializer(serializers.ModelSerializer):
    """
    Expose flags needed by the SPA guard + some RBAC context.
    """
    groups = serializers.SlugRelatedField(many=True, read_only=True, slug_field="name")
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_staff",
            "is_superuser",
            "groups",
            "permissions",
        )
        # keep your previous intent (email read-only) but still return it
        read_only_fields = ("id", "email", "is_staff", "is_superuser", "groups", "permissions")

    def get_permissions(self, obj):
        return _safe_permissions(obj)

# ---------- REGISTER ----------
class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password2 = serializers.CharField(write_only=True, trim_whitespace=False)

    class Meta:
        model = User
        fields = ("username", "email", "password", "password2", "first_name", "last_name")

    def validate_email(self, v):
        v = (v or "").strip().lower()
        if v and User.objects.filter(email=v).exists():
            raise serializers.ValidationError("Email is already registered.")
        return v

    def validate_username(self, v):
        v = (v or "").strip().lower()
        if User.objects.filter(username=v).exists():
            raise serializers.ValidationError("Username is taken.")
        return v

    def validate(self, attrs):
        pwd, pwd2 = attrs.get("password"), attrs.get("password2")
        if pwd != pwd2:
            raise serializers.ValidationError({"password2": "Passwords do not match."})
        password_validation.validate_password(pwd)
        return attrs

    def create(self, validated):
        password = validated.pop("password")
        validated.pop("password2", None)

        username = (validated.get("username") or "").strip().lower()
        email = (validated.get("email") or "").strip().lower()
        user = User(**{**validated, "username": username, "email": email})
        user.set_password(password)
        user.save()
        return user

# ---------- OPTIONAL: UPDATE NON-SENSITIVE FIELDS ----------
class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("username", "first_name", "last_name")

# ---------- PROFILE ----------
class ProfileSerializer(serializers.ModelSerializer):
    avatar_url = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Profile
        fields = ("phone", "avatar", "avatar_url")
        extra_kwargs = {
            "avatar": {"write_only": True, "required": False, "allow_null": True},
        }

    def get_avatar_url(self, obj):
        req = self.context.get("request")
        if obj and getattr(obj, "avatar", None):
            url = obj.avatar.url
            return req.build_absolute_uri(url) if req else url
        return None

# ---------- PASSWORD CHANGE ----------
class PasswordChangeSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True)
    new_password2 = serializers.CharField(write_only=True)

    def validate(self, data):
        if data["new_password"] != data["new_password2"]:
            raise serializers.ValidationError({"new_password2": "Passwords do not match."})
        user = self.context["request"].user
        if not user.check_password(data["old_password"]):
            raise serializers.ValidationError({"old_password": "Old password is incorrect."})
        return data

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
        return user
