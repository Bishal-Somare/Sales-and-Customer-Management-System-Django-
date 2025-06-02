# accounts/signals.py
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from django.db.models.signals import post_save # Keep for Profile signal
from django.contrib.auth.models import User # Keep for Profile signal
from .models import Profile # Keep for Profile signal

from notifications.utils import (
    add_notification_to_cache, 
    clear_user_notifications_from_cache,
    generate_inventory_status_notifications
)
import logging

logger = logging.getLogger(__name__)

@receiver(user_logged_in)
def handle_user_login_notifications(sender, request, user, **kwargs):
    logger.info(f"User {user.username} logged in. Populating notifications cache.")
    
    clear_user_notifications_from_cache(user)
    
    inventory_notifications = generate_inventory_status_notifications()
    if inventory_notifications:
        for notif_data in inventory_notifications:
            add_notification_to_cache(user, notif_data)
        logger.info(f"Added {len(inventory_notifications)} inventory notifications to cache for user {user.username}.")
    else:
        logger.info(f"No inventory notifications to add to cache for user {user.username} at login.")

@receiver(user_logged_out)
def handle_user_logout_notifications(sender, request, user, **kwargs):
    if user: 
        logger.info(f"User {user.username} logged out. Clearing notifications cache.")
        clear_user_notifications_from_cache(user)
    else:
        logger.info("User logged out (user object not available). Skipping cache clear for specific user.")

# Existing signal handler for Profile creation
@receiver(post_save, sender=User)
def handle_user_profile(sender, instance, created, **kwargs):
    """
    Signal handler to create or update a Profile when a User is saved.
    """
    if created:
        Profile.objects.create(user=instance)
        # print('Profile created!') # Consider using logger.info for consistency
        logger.info(f"Profile created for user {instance.username}")
    else:
        # Ensure profile exists before trying to save it, could be created manually
        if hasattr(instance, 'profile'):
            instance.profile.save()
            # print('Profile updated!')
            logger.info(f"Profile updated for user {instance.username}")
        else:
            # Handle cases where user exists but profile doesn't (e.g. manual DB change or if signal failed once)
            Profile.objects.create(user=instance)
            logger.info(f"Profile was missing, created now for user {instance.username}")