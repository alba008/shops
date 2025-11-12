from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import PasswordResetTokenGenerator
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes, force_str
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from django.template.loader import render_to_string
from django.core.mail import EmailMultiAlternatives

User = get_user_model()
token_gen = PasswordResetTokenGenerator()

@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_request(request):
    email = (request.data or {}).get("email")
    if not email:
        return Response({"detail": "Email is required"}, status=400)
    try:
        user = User.objects.get(email__iexact=email)
    except User.DoesNotExist:
        # Don't reveal existence; return 200
        return Response({"sent": True})

    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = token_gen.make_token(user)
    reset_url = f"{getattr(settings,'FRONTEND_URL','')}/reset-password?uid={uid}&token={token}"

    ctx = {
        "user": user,
        "reset_url": reset_url,
        "site_name": getattr(settings, "SITE_NAME", "Shop"),
        "site_domain": getattr(settings, "SITE_DOMAIN", "example.com"),
        "frontend_url": getattr(settings, "FRONTEND_URL", ""),
    }
    subj = f"{ctx['site_name']}: Reset your password"
    txt = render_to_string("emails/password_reset.txt", ctx)
    html = render_to_string("emails/password_reset.html", ctx)

    m = EmailMultiAlternatives(subj, txt, settings.DEFAULT_FROM_EMAIL, [user.email])
    m.attach_alternative(html, "text/html")
    m.send(fail_silently=False)
    return Response({"sent": True})

@api_view(["POST"])
@permission_classes([AllowAny])
def password_reset_confirm(request):
    uid = (request.data or {}).get("uid")
    token = (request.data or {}).get("token")
    new_password = (request.data or {}).get("new_password")
    if not (uid and token and new_password):
        return Response({"detail": "Missing fields"}, status=400)
    try:
        pk = force_str(urlsafe_base64_decode(uid))
        user = User.objects.get(pk=pk)
    except Exception:
        return Response({"detail": "Invalid link"}, status=400)
    if not token_gen.check_token(user, token):
        return Response({"detail": "Invalid/expired token"}, status=400)
    user.set_password(new_password)
    user.save()
    return Response({"ok": True})
