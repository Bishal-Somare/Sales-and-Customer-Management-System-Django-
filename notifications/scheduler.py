

# notifications/scheduler.py
from apscheduler.schedulers.background import BackgroundScheduler
from django.utils import timezone
from datetime import timedelta, date
from store.models import Item  # Assuming Item model is in store.models
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger(__name__)

def check_inventory_notifications():
    logger.info("Scheduler: Checking inventory for notifications...")
    
    notifications_to_send_payloads = [] # List of notification dicts for channel layer

    # Check for low stock items
    low_stock_items = Item.objects.filter(quantity__lt=10)
    for item in low_stock_items:
        notifications_to_send_payloads.append({
            'type': 'send_notification', # This will map to a method in your consumer
            'notification': {
                'id': f"low_stock_{item.id}_{timezone.now().timestamp()}", # Unique ID
                'product_name': item.name,
                'reason': 'Low Stock',
                'message': f"'{item.name}' is low in stock ({item.quantity} remaining)."
            }
        })

    # --- MODIFIED "Expiring Soon" LOGIC FOR DateField ---
    # Definition: Expiring soon = expiring_date is today or tomorrow.
    today_date = timezone.now().date()
    tomorrow_date = today_date + timedelta(days=1)

    # Items that have an expiry date, are not yet expired (implicitly, if expiring today/tomorrow),
    # and will expire either today or tomorrow.
    # Note: If an item's expiring_date IS today, it will also be caught by the "expired" logic
    # later if the scheduler runs after 00:00 on that day. You might want to consider
    # if you want both "expiring soon (today)" and "expired (today)" notifications.
    # For this example, we'll include items expiring today in "expiring soon".
    expiring_soon_items = Item.objects.filter(
        expiring_date__isnull=False,
        expiring_date__in=[today_date, tomorrow_date]
    ).exclude(expiring_date__lt=today_date) # Ensure we don't pick up past dates if data is odd

    for item in expiring_soon_items:
        if item.expiring_date: # Defensive check
            day_status = "today" if item.expiring_date == today_date else "tomorrow"
            notifications_to_send_payloads.append({
                'type': 'send_notification',
                'notification': {
                    'id': f"expiring_soon_{item.id}_{timezone.now().timestamp()}",
                    'product_name': item.name,
                    'reason': 'Expiring Soon',
                    'message': f"'{item.name}' is expiring {day_status} (on {item.expiring_date.strftime('%Y-%m-%d')})."
                }
            })
        else:
            # This case should ideally not happen with expiring_date__isnull=False
            logger.warning(f"Scheduler: Item {item.name} (ID: {item.id}) in expiring_soon_items has None expiry date despite query filter. Skipping.")
    
    # --- "Expired" LOGIC - message format adjusted ---
    # Definition: Expired = expiring_date is before today (or strictly before timezone.now() if you prefer more precision with DateField)
    # For DateField, expiring_date < today_date means it expired on any day before today.
    # expiring_date == today_date AND timezone.now().time() > 00:00:00 means it expired today.
    # The original `expiring_date__lt=timezone.now()` correctly handles this for DateField,
    # considering it expired if the current datetime is past 00:00:00 of the expiring_date.
    expired_items = Item.objects.filter(
        expiring_date__isnull=False,
        expiring_date__lt=timezone.now().date() # More explicit for DateField: expired if date is before today
                                                # Or, for items expiring *today*, keep original:
                                                # expiring_date__lt=timezone.now() - this means it's past 00:00 on its expiry date.
                                                # Let's stick to original for consistency with previous discussion,
                                                # as it means "as of this moment, has it passed the start of its expiry day?"
    )
    # Re-evaluating the "expired" logic slightly for clarity with DateField:
    # An item is expired if its `expiring_date` has passed.
    # If `expiring_date` is `2023-01-15` (a DateField), it's considered passed
    # once `timezone.now()` is `2023-01-15 00:00:00` or later.
    # So, `expiring_date__lt=timezone.now()` is correct for "has the expiry period started".

    # To be very precise: if today is `2023-01-15`, and item's `expiring_date` is `2023-01-15`.
    # `item.expiring_date` (as date) vs `timezone.now()` (as datetime)
    # `2023-01-15` vs `2023-01-15 10:00:00` -> `2023-01-15 00:00:00 < 2023-01-15 10:00:00` -> TRUE.

    expired_items = Item.objects.filter(
        expiring_date__isnull=False,
        expiring_date__lt=timezone.now() # This correctly treats DateField as YYYY-MM-DD 00:00:00
    )
    for item in expired_items:
        if item.expiring_date: # Defensive check
            notifications_to_send_payloads.append({
                'type': 'send_notification',
                'notification': {
                    'id': f"expired_{item.id}_{timezone.now().timestamp()}",
                    'product_name': item.name,
                    'reason': 'Expired',
                    'message': f"'{item.name}' has expired (on {item.expiring_date.strftime('%Y-%m-%d')})." # Changed format
                }
            })
        else:
            logger.warning(f"Scheduler: Item {item.name} (ID: {item.id}) in expired_items has None expiry date despite query filter. Skipping.")


    if not notifications_to_send_payloads:
        logger.info("Scheduler: No new notifications to send.")
    else:
        channel_layer = get_channel_layer()
        if not channel_layer:
            logger.error(f"Scheduler: Channel layer not available. Cannot send {len(notifications_to_send_payloads)} notifications.")
        else:
            logger.info(f"Scheduler: Found {len(notifications_to_send_payloads)} notifications to send to 'notifications_group'.")
            for notification_payload in notifications_to_send_payloads:
                async_to_sync(channel_layer.group_send)(
                    "notifications_group", # Name of the group
                    notification_payload
                )


def start():
    scheduler = BackgroundScheduler()
    # Run the check every 0.1 minute (6 seconds)
    scheduler.add_job(check_inventory_notifications, 'interval', minutes=0.1, id='inventory_check_job', replace_existing=True)
    try:
        scheduler.start()
        logger.info("APScheduler started...")
    except Exception as e:
        logger.error(f"Error starting APScheduler: {e}")

# --- Functions added to resolve ImportError from store.signals ---
# --- These also need to be updated for DateField logic ---

def get_inventory_notifications_data():
    """
    Gathers inventory notification data (low stock, expiring soon, expired)
    but does not send it. This function is added to satisfy imports from
    other modules like store.signals.
    Returns a list of notification data dictionaries.
    """
    logger.info("Scheduler (get_inventory_notifications_data): Gathering inventory data...")
    notifications_data = []
    
    # Low stock items
    low_stock_items = Item.objects.filter(quantity__lt=10)
    for item in low_stock_items:
        notifications_data.append({
            'id': f"low_stock_{item.id}_{timezone.now().timestamp()}",
            'product_name': item.name,
            'reason': 'Low Stock',
            'message': f"'{item.name}' is low in stock ({item.quantity} remaining)."
        })

    # --- MODIFIED "Expiring Soon" LOGIC FOR DateField ---
    today_date = timezone.now().date()
    tomorrow_date = today_date + timedelta(days=1)
    expiring_soon_items = Item.objects.filter(
        expiring_date__isnull=False,
        expiring_date__in=[today_date, tomorrow_date]
    ).exclude(expiring_date__lt=today_date)

    for item in expiring_soon_items:
        if item.expiring_date: # Defensive check
            day_status = "today" if item.expiring_date == today_date else "tomorrow"
            notifications_data.append({
                'id': f"expiring_soon_{item.id}_{timezone.now().timestamp()}",
                'product_name': item.name,
                'reason': 'Expiring Soon',
                'message': f"'{item.name}' is expiring {day_status} (on {item.expiring_date.strftime('%Y-%m-%d')})."
            })
        else:
            logger.warning(f"Scheduler (get_inventory_notifications_data): Item {item.name} (ID: {item.id}) in expiring_soon_items has None expiry date. Skipping.")

    # --- "Expired" LOGIC - message format adjusted ---
    expired_items = Item.objects.filter(
        expiring_date__isnull=False,
        expiring_date__lt=timezone.now() # Correctly handles DateField as YYYY-MM-DD 00:00:00
    )
    for item in expired_items:
        if item.expiring_date: # Defensive check
            notifications_data.append({
                'id': f"expired_{item.id}_{timezone.now().timestamp()}",
                'product_name': item.name,
                'reason': 'Expired',
                'message': f"'{item.name}' has expired (on {item.expiring_date.strftime('%Y-%m-%d')})." # Changed format
            })
        else:
            logger.warning(f"Scheduler (get_inventory_notifications_data): Item {item.name} (ID: {item.id}) in expired_items has None expiry date. Skipping.")
            
    logger.info(f"Scheduler (get_inventory_notifications_data): Found {len(notifications_data)} notification data points.")
    return notifications_data

def broadcast_notifications_to_group(group_name, notifications_list):
    """
    Broadcasts a list of notification messages (dictionaries) to a specified channel group.
    This function is added to satisfy imports from other modules like store.signals.
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
