

from django.db import models, transaction # Added transaction import
from django_extensions.db.fields import AutoSlugField
from store.models import Item
from accounts.models import Vendor, Customer
import decimal # Import decimal

DELIVERY_CHOICES = [("P", "Pending"), ("S", "Successful")]


class Sale(models.Model):
    """
    Represents a sale transaction involving a customer.
    """

    date_added = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Sale Date"
    )
    customer = models.ForeignKey(
        Customer,
        on_delete=models.DO_NOTHING,
        db_column="customer"
    )
    sub_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.0
    )
    # New discount fields
    discount_percentage = models.FloatField(default=0.0)
    discount_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    grand_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.0
    )
    # tax_amount = models.DecimalField( # Removed
    #     max_digits=10,
    #     decimal_places=2,
    #     default=0.0
    # )
    # tax_percentage = models.FloatField(default=0.0) # Removed
    amount_paid = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.0
    )
    amount_change = models.DecimalField( # This is typically change_returned = amount_paid - grand_total
        max_digits=10,
        decimal_places=2,
        default=0.0
    )

    class Meta:
        db_table = "sales"
        verbose_name = "Sale"
        verbose_name_plural = "Sales"

    def __str__(self):
        """
        Returns a string representation of the Sale instance.
        """
        return (
            f"Sale ID: {self.id} | "
            f"Grand Total: {self.grand_total} | "
            f"Date: {self.date_added}"
        )

    def sum_products(self):
        """
        Returns the total quantity of products in the sale.
        """
        return sum(detail.quantity for detail in self.saledetail_set.all())
        
    def get_items_display(self):
        """
        Returns a string of all item names in the sale, comma separated.
        """
        items = self.saledetail_set.all().select_related('item')
        return ", ".join([detail.item.name for detail in items]) if items else "No items"
        
    def get_primary_item(self):
        """
        Returns the first item in the sale, if any.
        """
        detail = self.saledetail_set.select_related('item').first()
        return detail.item if detail else None

    @property
    def amount_to_pay(self):
        """Returns the pending amount if grand_total > amount_paid, otherwise 0."""
        if self.grand_total is not None and self.amount_paid is not None:
            if self.grand_total > self.amount_paid:
                return self.grand_total - self.amount_paid
        return decimal.Decimal('0.00')


#sale lai render garni ho but sales detail chai sales kai page ma huncha
class SaleDetail(models.Model):
    """
    Represents details of a specific sale, including item and quantity.
    """

    sale = models.ForeignKey(
        Sale,
        on_delete=models.CASCADE,
        db_column="sale",
        related_name="saledetail_set"
    )
    item = models.ForeignKey(
        Item,
        on_delete=models.DO_NOTHING,
        db_column="item"
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )
    quantity = models.PositiveIntegerField()
    total_detail = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        db_table = "sale_details"
        verbose_name = "Sale Detail"
        verbose_name_plural = "Sale Details"

    def __str__(self):
        """
        Returns a string representation of the SaleDetail instance.
        """
        return (
            f"Detail ID: {self.id} | "
            f"Sale ID: {self.sale.id} | "
            f"Quantity: {self.quantity}"
        )


class Purchase(models.Model):
    """
    Represents a purchase of an item,
    including vendor details and delivery status.
    """

    slug = AutoSlugField(unique=True, populate_from="vendor")
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    description = models.TextField(max_length=300, blank=True, null=True)
    vendor = models.ForeignKey(
        Vendor, related_name="purchases", on_delete=models.CASCADE
    )
    order_date = models.DateTimeField(auto_now_add=True)
    delivery_date = models.DateTimeField(
        blank=True, null=True, verbose_name="Delivery Date"
    )
    quantity = models.PositiveIntegerField(default=0)
    delivery_status = models.CharField(
        choices=DELIVERY_CHOICES,
        max_length=1,
        default="P",
        verbose_name="Delivery Status",
    )
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.0,
        verbose_name="Price per item (RS)",
    )
    total_value = models.DecimalField(max_digits=10, decimal_places=2)

    def save(self, *args, **kwargs):
        """
        Calculates the total value and updates item quantity based on delivery status changes.
        """
        self.total_value = self.price * self.quantity

        with transaction.atomic():
            is_new = self._state.adding
            old_purchase_data = {}

            if not is_new:
                try:
                    # Fetch the original purchase instance from DB for comparison
                    original_purchase = Purchase.objects.get(pk=self.pk)
                    old_purchase_data['item_id'] = original_purchase.item_id
                    old_purchase_data['quantity'] = original_purchase.quantity
                    old_purchase_data['delivery_status'] = original_purchase.delivery_status
                except Purchase.DoesNotExist:
                    # Should not happen if not is_new, but if it does, old_purchase_data remains empty
                    # and logic will proceed as if no prior state to undo.
                    pass

            super().save(*args, **kwargs)  # Save the Purchase instance itself

            # --- Item Quantity Adjustment Logic ---

            # "Undo" effect of the old state if it was 'Successful'
            if not is_new and old_purchase_data.get('delivery_status') == "S":
                try:
                    item_to_undo = Item.objects.get(pk=old_purchase_data['item_id'])
                    item_to_undo.quantity -= old_purchase_data['quantity']
                    item_to_undo.save()
                except Item.DoesNotExist:
                    # Log this error or handle as appropriate if the item was unexpectedly deleted
                    print(f"Warning: Item with ID {old_purchase_data['item_id']} not found for undoing quantity.")


            # "Apply" effect of the new state if it is 'Successful'
            if self.delivery_status == "S":
                # self.item is the current item associated with the purchase
                # self.quantity is the current quantity of the purchase
                try:
                    # Ensure we are acting on the correct item instance from the DB
                    current_item_instance = Item.objects.get(pk=self.item.id)
                    current_item_instance.quantity += self.quantity
                    current_item_instance.save()
                except Item.DoesNotExist:
                    # Log this error or handle as appropriate
                     print(f"Warning: Item with ID {self.item.id} not found for applying quantity.")


    def __str__(self):
        """
        Returns a string representation of the Purchase instance.
        """
        return str(self.item.name)

    class Meta:
        ordering = ["order_date"]
