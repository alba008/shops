# core/notify.py
from django.core.mail import send_mail, EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings

def notify_admin(subject, template, ctx, to=None):
    """
    Send an HTML email to you/your team for internal events (new order, low stock).
    - subject: Email subject line
    - template: Path to HTML template (e.g., 'emails/order_admin.html')
    - ctx: Dict passed to the template
    - to: Optional list of recipients; defaults to a single admin email
    """
    html = render_to_string(template, ctx)
    recipients = to or [getattr(settings, "ADMIN_ALERT_EMAIL", "lilian@blsuntechdynamics.com")]
    send_mail(subject, "", None, recipients, html_message=html)

def email_customer(to_email, subject, template, ctx, reply_to=None, attachments=None):
    """
    Send an HTML email to a customer (order confirmation, shipping notice).
    - to_email: Customer email
    - reply_to: Optional list like ['support@yourdomain.com']
    - attachments: Optional list of (filename, content_bytes, mimetype)
    """
    html = render_to_string(template, ctx)
    msg = EmailMultiAlternatives(
        subject=subject,
        body="",  # we’re sending HTML
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        to=[to_email],
        reply_to=reply_to or [getattr(settings, "SUPPORT_EMAIL", "lilian@blsuntechdynamics.com")],
    )
    msg.attach_alternative(html, "text/html")
    for att in (attachments or []):
        msg.attach(*att)  # (filename, content, mimetype)
    msg.send()
