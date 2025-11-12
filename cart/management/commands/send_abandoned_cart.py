from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from cart.models import CartSnapshot
from orders.models import Order

class Command(BaseCommand):
    help = "Send abandoned cart emails"

    def add_arguments(self, parser):
        parser.add_argument("--hours", type=int, default=6)

    def handle(self, *args, **opts):
        cutoff = timezone.now() - timedelta(hours=opts["hours"])
        qs = CartSnapshot.objects.filter(updated__lte=cutoff).order_by("-updated")
        sent = 0
        for snap in qs:
            to = (snap.user.email if snap.user and snap.user.email else snap.email).strip()
            if not to:
                continue
            # Skip if user has ordered after snapshot
            if snap.user and Order.objects.filter(email=snap.user.email, created__gte=snap.updated).exists():
                continue
            ctx = {
                "items": [{"name": i.get("name","Item"), "qty": i.get("qty",1), "price": i.get("price","")} for i in snap.data.get("items", [])],
                "site_name": getattr(settings, "SITE_NAME", "Shop"),
                "site_domain": getattr(settings, "SITE_DOMAIN", "example.com"),
                "frontend_url": getattr(settings, "FRONTEND_URL", ""),
            }
            subj = f"{ctx['site_name']}: You left something behind"
            txt = render_to_string("emails/abandoned_cart.txt", ctx)
            html = render_to_string("emails/abandoned_cart.html", ctx)
            m = EmailMultiAlternatives(subj, txt, settings.DEFAULT_FROM_EMAIL, [to])
            m.attach_alternative(html, "text/html")
            m.send(fail_silently=False)
            sent += 1
        self.stdout.write(self.style.SUCCESS(f"Sent {sent} abandoned cart emails"))
