# accounts/views_profile.py
from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from .serializers import ProfileSerializer, PasswordChangeSerializer

def _nostore_headers(): return {"Cache-Control": "no-store"}

class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        ser = ProfileSerializer(request.user.profile, context={"request": request})
        return Response(ser.data, headers=_nostore_headers())

    def patch(self, request):
        # supports both multipart/form-data (avatar) and JSON
        ser = ProfileSerializer(
            request.user.profile,
            data=request.data,
            partial=True,
            context={"request": request},
        )
        if ser.is_valid():
            ser.save()
            return Response(ser.data, headers=_nostore_headers())
        return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST, headers=_nostore_headers())


class PasswordChangeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        ser = PasswordChangeSerializer(data=request.data, context={"request": request})
        if ser.is_valid():
            ser.save()
            return Response({"detail": "Password updated."}, status=200, headers=_nostore_headers())
        return Response(ser.errors, status=400, headers=_nostore_headers())
