# accounts/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .emails import send_welcome   # <-- import the helper

User = get_user_model()

@receiver(post_save, sender=User)
def send_welcome_on_signup(sender, instance: User, created, **kwargs):
    if created:
        send_welcome(instance)
