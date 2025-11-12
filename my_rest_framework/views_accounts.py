# my_rest_framework/views_accounts.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

class AccountsMeView(APIView):
    authentication_classes = []  # or Session/JWT if you want
    permission_classes = []      # AllowAny for now

    def get(self, request):
        user = getattr(request, "user", None)
        if user and user.is_authenticated:
            return Response({
                "id": user.id,
                "email": user.email,
                "first_name": getattr(user, "first_name", ""),
                "last_name": getattr(user, "last_name", ""),
                "is_authenticated": True,
            })
        # anonymous fallback so frontend stops erroring
        return Response({
            "id": None,
            "email": "",
            "first_name": "",
            "last_name": "",
            "is_authenticated": False,
        })
