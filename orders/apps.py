from django.apps import AppConfig
import logging

logger = logging.getLogger(__name__)

class OrdersConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'orders'

    def ready(self):
        logger.info("OrdersConfig.ready(): importing orders.signals")
        from . import signals  # noqa
