# notifications/apps.py
from django.apps import AppConfig
import logging # Added for logger

logger = logging.getLogger(__name__) # Added for logger

class NotificationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'notifications'

    def ready(self):
        # APScheduler startup logic is removed.
        logger.info("Notifications app ready. Event-driven notification logic active.")
        pass