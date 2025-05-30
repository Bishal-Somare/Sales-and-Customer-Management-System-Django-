

from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Purchase


# @receiver(post_save, sender=Purchase)
# def update_item_quantity(sender, instance, created, **kwargs):
#     """
#     Signal to update item quantity when a purchase is made.
#     This function's logic has been moved to the Purchase model's save() method
#     to handle status changes and updates more robustly.
#     """
#     # if created: # Original problematic logic
#     #     instance.item.quantity += instance.quantity
#     #     instance.item.save()
pass # Signal handler is now disabled/inactive.

