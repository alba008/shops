# customers/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Customer
from accounts.emails import send_welcome

@receiver(post_save, sender=Customer)
def welcome_on_customer(sender, instance, created, **kwargs):
    if created and instance.user and instance.user.email:
        send_welcome(instance.user)
