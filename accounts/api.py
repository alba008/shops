# accounts/api.py
from rest_framework.decorators import api_view, permission_classes, parser_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser, MultiPartParser, FormParser
from rest_framework.response import Response

from .serializers import UserSerializer


@api_view(["GET", "PATCH"])
@permission_classes([IsAuthenticated])
@parser_classes([JSONParser, MultiPartParser, FormParser])
def me(request):
    """
    /api/accounts/me/
    GET   -> return current user via UserSerializer
    PATCH -> partial update of current user (e.g. first_name, last_name, username)
    """
    user = request.user

    if request.method == "GET":
        # Use the same serializer as your other views
        data = UserSerializer(user).data
        return Response(data)

    # PATCH
    serializer = UserSerializer(
        user,
        data=request.data,
        partial=True,
    )
    serializer.is_valid(raise_exception=True)
    serializer.save()
    return Response(serializer.data)
