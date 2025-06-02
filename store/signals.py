# store/signals.py
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from datetime import timedelta

from .models import Item 
# from transactions.models import Sale, SaleDetail # Not directly used in this signal handler

from notifications.utils import broadcast_notification_via_ws
import logging

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Item)
def item_saved_handler(sender, instance, created, **kwargs):
    logger.info(f"Item saved: {instance.name} (ID: {instance.id}), Created: {created}, Qty: {instance.quantity}. Checking for notifications.")
    notifications_to_broadcast = []

    # Check for low stock
    if instance.quantity < 10: 
        notifications_to_broadcast.append({
            'id': f"low_stock_{instance.id}_{timezone.now().timestamp()}",
            'product_name': instance.name,
            'reason': 'Low Stock',
            'message': f"'{instance.name}' is now low in stock ({instance.quantity} remaining)."
        })

    # Check for expiry status
    if instance.expiring_date:
        today_date = timezone.now().date()
        tomorrow_date = today_date + timedelta(days=1)

        if instance.expiring_date < today_date: 
            notifications_to_broadcast.append({
                'id': f"expired_{instance.id}_{timezone.now().timestamp()}",
                'product_name': instance.name,
                'reason': 'Expired',
                'message': f"'{instance.name}' has expired (on {instance.expiring_date.strftime('%Y-%m-%d')})."
            })
        elif instance.expiring_date == today_date: 
            notifications_to_broadcast.append({
                'id': f"expiring_soon_{instance.id}_{timezone.now().timestamp()}",
                'product_name': instance.name,
                'reason': 'Expiring Soon',
                'message': f"'{instance.name}' is expiring today (on {instance.expiring_date.strftime('%Y-%m-%d')})."
            })
        elif instance.expiring_date == tomorrow_date: 
             notifications_to_broadcast.append({
                'id': f"expiring_soon_{instance.id}_{timezone.now().timestamp()}",
                'product_name': instance.name,
                'reason': 'Expiring Soon',
                'message': f"'{instance.name}' is expiring tomorrow (on {instance.expiring_date.strftime('%Y-%m-%d')})."
            })
    
    unique_notifications = []
    seen_ids_bases = set() 

    # Prioritize 'Expired', then 'Expiring Soon', then 'Low Stock' if multiple conditions met for the same item
    # Order of appending to notifications_to_broadcast already somewhat handles this,
    # but this ensures only one of each "type" per item is sent, preferring the most critical.
    
    # Example: If an item is both "Expired" and "Low Stock", only "Expired" might be sent
    # depending on how you want to handle this. The current logic will send both.
    # If you want only the "most critical" (e.g., Expired > Expiring Soon > Low Stock),
    # you would build the list and then filter.

    # The provided logic sends multiple if conditions match (e.g. low stock AND expiring).
    # Let's stick to that for now as "unique_notifications" part was slightly ambiguous.
    # The original unique_notifications logic was trying to prevent duplicate type for *same item*
    # but the ID generation with timestamp already makes them unique.

    for notif_data in notifications_to_broadcast:
        broadcast_notification_via_ws(notif_data)


# Removed Sale signal handler as Item signal covers stock changes due to sales
# @receiver(post_save, sender=Sale)
# def sale_saved_handler(sender, instance, created, **kwargs):
#     logger.info(f"Sale {'created' if created else 'updated'}: ID {instance.id}. Item stock changes handled by Item post_save signal.")
#     pass 