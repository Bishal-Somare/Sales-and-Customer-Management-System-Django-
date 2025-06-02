# notifications/utils.py
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from store.models import Item
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
import logging

logger = logging.getLogger(__name__)

CACHE_TIMEOUT = 60 * 60 * 24  # 24 hours, or None for indefinite for locmem

# --- Cache Utilities ---
def get_user_cache_key(user):
    return f"user_{user.id}_notifications"

def add_notification_to_cache(user, notification_data):
    if not user or not user.is_authenticated:
        return

    cache_key = get_user_cache_key(user)
    notifications = cache.get(cache_key, [])
    
    # Ensure notification_data is a dict and has an 'id'
    if not isinstance(notification_data, dict) or 'id' not in notification_data:
        logger.warning(f"Attempted to add invalid notification_data to cache for user {user.id}: {notification_data}")
        return

    if any(n['id'] == notification_data['id'] for n in notifications):
        logger.debug(f"Notification {notification_data['id']} already in cache for user {user.id}. Skipping.")
        return

    notifications.append(dict(notification_data)) # Ensure it's a new dict
    # Sort by timestamp in ID for newest first. Assumes ID format "type_itemid_timestamp"
    notifications.sort(key=lambda x: float(x['id'].split('_')[-1]), reverse=True)
    
    cache.set(cache_key, notifications, CACHE_TIMEOUT)
    logger.debug(f"Added notification {notification_data['id']} to cache for user {user.id}. Cache size: {len(notifications)}")

def get_notifications_from_cache(user):
    if not user or not user.is_authenticated:
        return []
    cache_key = get_user_cache_key(user)
    notifications = cache.get(cache_key, [])
    logger.debug(f"Retrieved {len(notifications)} notifications from cache for user {user.id}.")
    return notifications

def remove_notification_from_cache(user, notification_id):
    if not user or not user.is_authenticated:
        return False
    cache_key = get_user_cache_key(user)
    notifications = cache.get(cache_key, [])
    initial_len = len(notifications)
    notifications = [n for n in notifications if n.get('id') != notification_id] # Safe access with .get()
    if len(notifications) < initial_len:
        cache.set(cache_key, notifications, CACHE_TIMEOUT)
        logger.debug(f"Removed notification {notification_id} from cache for user {user.id}. Cache size: {len(notifications)}")
        return True
    logger.debug(f"Notification {notification_id} not found in cache for user {user.id} for removal.")
    return False

def clear_user_notifications_from_cache(user):
    if not user or not user.is_authenticated:
        return
    cache_key = get_user_cache_key(user)
    cache.delete(cache_key)
    logger.info(f"Cleared notifications cache for user {user.id}.")

# --- Notification Generation Utility ---
def generate_inventory_status_notifications():
    logger.info("Util: Generating current inventory status notifications...")
    current_notifications = []

    # Low stock items
    low_stock_items = Item.objects.filter(quantity__lt=10) # Threshold = 10
    for item in low_stock_items:
        current_notifications.append({
            'id': f"low_stock_{item.id}_{timezone.now().timestamp()}",
            'product_name': item.name,
            'reason': 'Low Stock',
            'message': f"'{item.name}' is low in stock ({item.quantity} remaining)."
        })

    # Expiring soon & Expired items
    today_date = timezone.now().date()
    tomorrow_date = today_date + timedelta(days=1)

    # Expiring Soon (Today or Tomorrow)
    expiring_soon_items = Item.objects.filter(
        expiring_date__isnull=False,
        expiring_date__in=[today_date, tomorrow_date]
    ).exclude(expiring_date__lt=today_date)

    for item in expiring_soon_items:
        if item.expiring_date: 
            day_status = "today" if item.expiring_date == today_date else "tomorrow"
            current_notifications.append({
                'id': f"expiring_soon_{item.id}_{timezone.now().timestamp()}",
                'product_name': item.name,
                'reason': 'Expiring Soon',
                'message': f"'{item.name}' is expiring {day_status} (on {item.expiring_date.strftime('%Y-%m-%d')})."
            })

    # Expired Items (expiry date is before current moment)
    expired_items = Item.objects.filter(
        expiring_date__isnull=False,
        expiring_date__lt=timezone.now() 
    )
    for item in expired_items:
        # Avoid duplicate "Expired" if also caught by "Expiring Soon today" by checking it's not also expiring_soon today
        is_also_expiring_today = any(
            n.get('reason') == 'Expiring Soon' and n.get('product_name') == item.name and "today" in n.get('message', '')
            for n in current_notifications
        )
        if not is_also_expiring_today and item.expiring_date:
             current_notifications.append({
                'id': f"expired_{item.id}_{timezone.now().timestamp()}",
                'product_name': item.name,
                'reason': 'Expired',
                'message': f"'{item.name}' has expired (on {item.expiring_date.strftime('%Y-%m-%d')})."
            })
            
    logger.info(f"Util: Generated {len(current_notifications)} inventory status notifications.")
    return current_notifications

# --- Broadcasting Utility (for WebSockets) ---
def broadcast_notification_via_ws(notification_data):
    channel_layer = get_channel_layer()
    if channel_layer:
        async_to_sync(channel_layer.group_send)(
            "notifications_group",
            {
                'type': 'send_notification', 
                'notification': notification_data
            }
        )
        logger.info(f"Broadcasted WS notification: {notification_data.get('reason')} - {notification_data.get('message')}")
    else:
        logger.error("Cannot broadcast WS notification: Channel layer not available.")