# notifications/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone
from datetime import timedelta
from store.models import Item  # Assuming Item model is in store.models
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger(__name__)

def check_inventory_notifications():
    logger.info("Scheduler: Checking inventory for notifications...")
    channel_layer = get_channel_layer()
    notifications_to_send = []

    # Check for low stock items
    low_stock_items = Item.objects.filter(quantity__lt=10)
    for item in low_stock_items:
        notifications_to_send.append({
            'type': 'send_notification', # This will map to a method in your consumer
            'notification': {
                'id': f"low_stock_{item.id}_{timezone.now().timestamp()}", # Unique ID
                'product_name': item.name,
                'reason': 'Low Stock',
                'message': f"'{item.name}' is low in stock ({item.quantity} remaining)."
            }
        })

    # Check for soon-to-expire items (e.g., expiring in the next 3 minutes)
    # We use a 4-minute window to ensure items expiring in "just under 3 minutes" are caught
    # and to account for scheduler run intervals.
    soon_time_threshold_start = timezone.now()
    soon_time_threshold_end = timezone.now() + timedelta(minutes=0.5) # Check for items expiring *within* the next 3 mins

    # Items that have an expiry date, are not yet expired, but will expire soon
    expiring_soon_items = Item.objects.filter(
        expiring_date__isnull=False,
        expiring_date__gt=soon_time_threshold_start, # Not yet expired
        expiring_date__lte=soon_time_threshold_end  # Will expire within the next 3 minutes
    )
    for item in expiring_soon_items:
        notifications_to_send.append({
            'type': 'send_notification',
            'notification': {
                'id': f"expiring_soon_{item.id}_{timezone.now().timestamp()}",
                'product_name': item.name,
                'reason': 'Expiring Soon',
                'message': f"'{item.name}' is expiring soon (at {item.expiring_date.strftime('%Y-%m-%d %H:%M')})."
            }
        })
    
    # Check for already expired items (for completeness, though "soon-to-expire" is the primary goal)
    expired_items = Item.objects.filter(
        expiring_date__isnull=False,
        expiring_date__lt=timezone.now()
    )
    for item in expired_items:
        notifications_to_send.append({
            'type': 'send_notification',
            'notification': {
                'id': f"expired_{item.id}_{timezone.now().timestamp()}",
                'product_name': item.name,
                'reason': 'Expired',
                'message': f"'{item.name}' has expired (on {item.expiring_date.strftime('%Y-%m-%d %H:%M')})."
            }
        })


    if notifications_to_send and channel_layer:
        logger.info(f"Scheduler: Found {len(notifications_to_send)} notifications to send.")
        for notification_data in notifications_to_send:
            async_to_sync(channel_layer.group_send)(
                "notifications_group", # Name of the group
                notification_data
            )
    elif not notifications_to_send:
        logger.info("Scheduler: No new notifications to send.")


def start():
    scheduler = BackgroundScheduler()
    # Run the check every 1 minute
    scheduler.add_job(check_inventory_notifications, 'interval', minutes=0.1, id='inventory_check_job', replace_existing=True)
    try:
        scheduler.start()
        logger.info("APScheduler started...")
    except Exception as e:
        logger.error(f"Error starting APScheduler: {e}")