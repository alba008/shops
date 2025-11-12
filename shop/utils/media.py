# shop/utils/media.py
from django.conf import settings

def ensure_media_url(path: str) -> str:
    if not path:
        return f"{settings.MEDIA_URL.rstrip('/')}/placeholder.png"
    s = str(path).strip()
    if s.startswith("http://") or s.startswith("https://"):
        return s
    if s.startswith("/media/"):
        return s
    # bare filename -> /media/<file>
    return f"{settings.MEDIA_URL.rstrip('/')}/{s.lstrip('/')}"
