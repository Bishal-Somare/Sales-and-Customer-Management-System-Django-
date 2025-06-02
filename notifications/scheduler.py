# notifications/scheduler.py
from django.utils import timezone 
from datetime import timedelta, date
# from store.models import Item # Not directly used here anymore
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

# Import from the new utils module
from .utils import generate_inventory_status_notifications # Removed broadcast_notification_via_ws as it's not used by this file

logger = logging.getLogger(__name__)

# APScheduler `start` function and `BackgroundScheduler` are removed.
# The `check_inventory_notifications` job function is also removed.

def get_inventory_notifications_data():
    """
    Retained for compatibility if other modules import it.
    Delegates to the new utility function for generating notifications.
    """
    logger.info("notifications.scheduler.get_inventory_notifications_data: Delegating to utils.")
    return generate_inventory_status_notifications()

def broadcast_notifications_to_group(group_name, notifications_list):
    """
    Retained for compatibility. Broadcasts a list of notification messages.
    Consider using `broadcast_notification_via_ws(notification_data)` from utils for new code.
    """
    channel_layer = get_channel_layer()
    if not channel_layer:
        logger.error(f"Scheduler (broadcast_notifications_to_group): Channel layer not available. Cannot send to group {group_name}.")
        return

    if not notifications_list:
        logger.info(f"Scheduler (broadcast_notifications_to_group): No notifications to send to group {group_name}.")
        return

    logger.info(f"Scheduler (broadcast_notifications_to_group): Sending {len(notifications_list)} notifications to group {group_name}...")
    for notification_content in notifications_list:
        async_to_sync(channel_layer.group_send)(
            group_name,
            {
                'type': 'send_notification', 
                'notification': notification_content 
            }
        )
    logger.info(f"Scheduler (broadcast_notifications_to_group): Finished sending notifications to group {group_name}.")