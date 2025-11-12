# myshop/myshop/views.py
from django.http import JsonResponse
from django.middleware.csrf import get_token

def csrf_view(request):
    """
    Return a CSRF token so the React app can store and send it.
    """
    return JsonResponse({"csrftoken": get_token(request)})
