# mail/signals.py
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver

from orders.models import Order  # <-- your orders app
from .mailer import send_order_buyer, send_order_seller

@receiver(pre_save, sender=Order)
def _remember_paid(sender, instance: Order, **kwargs):
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._was_paid = old.paid
        except sender.DoesNotExist:
            instance._was_paid = False
    else:
        instance._was_paid = False

@receiver(post_save, sender=Order)
def _notify_on_paid(sender, instance: Order, created, **kwargs):
    paid_now = bool(instance.paid)
    was_paid = bool(getattr(instance, "_was_paid", False))
    if paid_now and not was_paid:
        try:
            if instance.email:
                send_order_buyer(instance)
            send_order_seller(instance)
        except Exception as e:
            print("Order emails failed:", e)
