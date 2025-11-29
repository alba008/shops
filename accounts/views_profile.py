# accounts/views_profile.py
from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .serializers import ProfileSerializer, PasswordChangeSerializer
from .models import Profile


def _nostore_headers():
    return {"Cache-Control": "no-store"}


class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, MultiPartParser, FormParser]

    def _get_profile(self, request):
        # Ensure profile always exists
        profile, _ = Profile.objects.get_or_create(user=request.user)
        return profile

    def get(self, request):
        profile = self._get_profile(request)
        ser = ProfileSerializer(profile, context={"request": request})
        return Response(ser.data, headers=_nostore_headers())

    def patch(self, request):
        profile = self._get_profile(request)
        ser = ProfileSerializer(
            profile,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        if ser.is_valid():
            ser.save()
            return Response(ser.data, headers=_nostore_headers())
        return Response(
            ser.errors,
            status=status.HTTP_400_BAD_REQUEST,
            headers=_nostore_headers(),
        )


class PasswordChangeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ser = PasswordChangeSerializer(data=request.data, context={"request": request})
        if ser.is_valid():
            ser.save()
            return Response(
                {"detail": "Password updated."},
                status=200,
                headers=_nostore_headers(),
            )
        return Response(ser.errors, status=400, headers=_nostore_headers())
