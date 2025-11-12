# accounts/emails.py
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

def send_welcome(user):
    """Send the welcome email to a user."""
    if not getattr(user, "email", None):
        return 0
    ctx = {
        "user": user,
        "site_name": getattr(settings, "SITE_NAME", "Shop"),
        "site_domain": getattr(settings, "SITE_DOMAIN", "example.com"),
        "frontend_url": getattr(settings, "FRONTEND_URL", ""),
    }
    subj = f"{ctx['site_name']}: Welcome!"
    txt = render_to_string("emails/welcome.txt", ctx)
    html = render_to_string("emails/welcome.html", ctx)
    m = EmailMultiAlternatives(subj, txt, settings.DEFAULT_FROM_EMAIL, [user.email])
    m.attach_alternative(html, "text/html")
    return m.send(fail_silently=False)
