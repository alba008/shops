# assistant/views.py

from typing import List, Dict, Any

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from .llm_chat import generate_shop_reply


@api_view(["POST"])
@permission_classes([AllowAny])
def shop_assistant_view(request):
    """
    Request body:
    {
      "messages": [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello!"},
        {"role": "user", "content": "I need socks for running"}
      ],
      "context": { ...optional extra info... }
    }
    """
    data: Dict[str, Any] = request.data or {}
    history: List[Dict[str, str]] = data.get("messages") or []

    if not isinstance(history, list) or not history:
        return Response(
            {"error": "messages must be a non-empty list"},
            status=status.HTTP_400_BAD_REQUEST,
        )

    store_context = data.get("context") or {}
    reply = generate_shop_reply(history, store_context=store_context)
    return Response({"reply": reply})
