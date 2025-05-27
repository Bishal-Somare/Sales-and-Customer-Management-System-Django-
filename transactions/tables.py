import django_tables2 as tables
from .models import Sale, Purchase


class SaleTable(tables.Table):
    items = tables.Column(accessor='get_items_display', verbose_name='Items')
    
    class Meta:
        model = Sale
        template_name = "django_tables2/semantic.html" # Or your preferred bootstrap template
        fields = (
            'id',
            'date_added',
            'customer',
            'items',
            'sub_total',
            'discount_percentage',
            'discount_amount',
            'grand_total',
            'amount_paid',
            # 'amount_to_pay', # Removed this field from table definition
            'amount_change'
        )
        # If you use django-tables2 for rendering, you'd also remove 'amount_to_pay' here.
        # However, sales_list.html directly uses sales_table.html as an include,
        # so the change in sales_table.html is the primary one for display.
        # This change is for consistency if SaleTable class is used elsewhere by django-tables2.
        order_by_field = 'sort'


class PurchaseTable(tables.Table):
    class Meta:
        model = Purchase
        template_name = "django_tables2/semantic.html"
        fields = (
            'item',
            'vendor',
            'order_date',
            'delivery_date',
            'quantity',
            'delivery_status',
            'price',
            'total_value'
        )
        order_by_field = 'sort'