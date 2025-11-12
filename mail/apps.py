from django.apps import AppConfig

class MailConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mail"                 # <-- EXACT
    def ready(self):
        from . import signals      # keep if you use signals
