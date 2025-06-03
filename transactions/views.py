# transactions/views.py

# Standard library imports
import json
import logging
import decimal # Import decimal

# Django core imports
from django.http import JsonResponse, HttpResponse
from django.urls import reverse, reverse_lazy
from django.shortcuts import render, get_object_or_404
from django.db import transaction as django_transaction
from django.db.models import Prefetch
from django.contrib.auth.decorators import login_required, user_passes_test
from django.views.decorators.http import require_POST

# Class-based views
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

# Authentication and permissions
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

# Third-party packages
from openpyxl import Workbook
from django.contrib import messages

# Local app imports
from store.models import Item
from accounts.models import Customer
from .models import Sale, Purchase, SaleDetail
from .forms import PurchaseForm
from django.db.models import Q
from functools import reduce
import operator
from django.template.loader import render_to_string
import pdfkit # Ensure pdfkit is installed: pip install pdfkit

logger = logging.getLogger(__name__)

# Configure path to wkhtmltopdf.exe or ensure it's in your system PATH
# If you remove this, make sure wkhtmltopdf is in your PATH.
try:
    config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe')
except OSError:
    logger.warning("wkhtmltopdf not found at specified path. PDF generation might fail. Ensure it's in your system PATH or configure the path here.")
    config = None


def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'

# --- PDF and Excel Export functions ---
def render_to_pdf(template_src, context_dict={}):
    # Check if config is None AND if pdfkit's default configuration can find wkhtmltopdf
    # This allows wkhtmltopdf to be found if it's in PATH even if explicit config failed/was not set
    current_config = config
    if not current_config:
        try: # Attempt to find in PATH if not configured
            current_config = pdfkit.configuration() # Tries to find wkhtmltopdf in PATH
        except OSError: # wkhtmltopdf not found in PATH either
            logger.error("PDF generation skipped: wkhtmltopdf not found or configured.")
            return HttpResponse("PDF generation service is not configured correctly. Please ensure wkhtmltopdf is installed and in your system PATH, or configured in the application.", status=500)


    html_content = render_to_string(template_src, context_dict)
    options = {
        'page-size': 'A4', 'encoding': 'UTF-8', 'enable-local-file-access': '',
        'no-outline': None, 'orientation' : 'landscape', 'margin-top': '5mm',
        'margin-right': '5mm', 'margin-bottom': '5mm', 'margin-left': '5mm',
        'zoom': '1.0', 'viewport-size': '1280x1024',
        'custom-header': [ # Added for potential compatibility issues
            ('Accept-Encoding', 'gzip')
        ],
        'no-stop-slow-scripts': None # Added for potential JS heavy pages
    }
    try:
        pdf = pdfkit.from_string(html_content, False, configuration=current_config, options=options)
        if pdf:
            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = 'inline; filename="report.pdf"'
            return response
    except Exception as e:
        # More specific error logging if possible
        detailed_error = str(e)
        if "Done" in detailed_error and "Error" in detailed_error: # Common pattern for wkhtmltopdf errors
            logger.error(f"PDF generation failed with wkhtmltopdf error: {detailed_error}", exc_info=False) # No need for full stack trace if it's a wkhtmltopdf issue
        else:
            logger.error(f"PDF generation failed: {e}", exc_info=True)
    return HttpResponse("PDF generation failed. An error occurred, please check server logs.", status=500)

def export_detailed_sales_to_pdf(request, pk):
    sale = get_object_or_404(
        Sale.objects.select_related('customer').prefetch_related(
            Prefetch('saledetail_set', queryset=SaleDetail.objects.select_related('item'))
        ), id=pk
    )
    context = {'sale': sale}
    return render_to_pdf('transactions/sale_ticket.html', context)

def export_sales_to_pdf(request):
    sales = Sale.objects.all().select_related('customer').prefetch_related(
        Prefetch('saledetail_set', queryset=SaleDetail.objects.select_related('item'))
    )
    context = {'sales': sales}
    return render_to_pdf('transactions/sales_table.html', context)

def export_sales_to_excel(request):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = 'Sales'
    columns = [
        'ID', 'Date', 'Customer', 'Items', 'Sub Total', 'Discount %', 'Discount Amount',
        'Grand Total', 'Amount Paid', 'Amount Change'
    ]
    worksheet.append(columns)
    sales = Sale.objects.all().prefetch_related('saledetail_set__item', 'customer')
    for sale in sales:
        customer_identifier = sale.customer.get_full_name() if sale.customer else "N/A"
        date_added_naive = sale.date_added.replace(tzinfo=None) if sale.date_added and sale.date_added.tzinfo else sale.date_added
        worksheet.append([
            sale.id, date_added_naive, customer_identifier, sale.get_items_display(),
            sale.sub_total, sale.discount_percentage, sale.discount_amount,
            sale.grand_total, sale.amount_paid, sale.amount_change
        ])
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=sales.xlsx'
    workbook.save(response)
    return response

def export_purchases_to_excel(request):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = 'Purchases'
    columns = [
        'ID', 'Item', 'Description', 'Vendor', 'Order Date', 'Delivery Date',
        'Quantity', 'Delivery Status', 'Price per item (Rs)', 'Total Value'
    ]
    worksheet.append(columns)
    purchases = Purchase.objects.all().select_related('item', 'vendor')
    for purchase in purchases:
        delivery_date_naive = purchase.delivery_date.replace(tzinfo=None) if purchase.delivery_date and purchase.delivery_date.tzinfo else purchase.delivery_date
        order_date_naive = purchase.order_date.replace(tzinfo=None) if purchase.order_date and purchase.order_date.tzinfo else purchase.order_date
        worksheet.append([
            purchase.id, purchase.item.name, purchase.description, purchase.vendor.name,
            order_date_naive, delivery_date_naive, purchase.quantity,
            purchase.get_delivery_status_display(), purchase.price, purchase.total_value
        ])
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=purchases.xlsx'
    workbook.save(response)
    return response

# --- ListView and DetailView classes ---
class SaleListView(LoginRequiredMixin, ListView):
    model = Sale
    template_name = "transactions/sales_list.html"
    context_object_name = "sales"
    paginate_by = 40
    ordering = ['-date_added']

    def get_queryset(self):
        return Sale.objects.all().select_related('customer').prefetch_related(
            Prefetch('saledetail_set', queryset=SaleDetail.objects.select_related('item'))
        ).order_by(*self.ordering)

class SaleDetailView(LoginRequiredMixin, DetailView):
    model = Sale
    template_name = "transactions/saledetail.html"

    def get_queryset(self):
        return Sale.objects.select_related('customer').prefetch_related(
            Prefetch('saledetail_set', queryset=SaleDetail.objects.select_related('item'))
        )

@login_required
def SaleCreateView(request):
    context = {
        "active_icon": "sales",
        "customers": [c.to_select2() for c in Customer.objects.all()]
    }
    if request.method == 'POST':
        if is_ajax(request=request):
            try:
                data = json.loads(request.body)
                logger.info(f"SaleCreateView POST data: {data}")

                required_fields = ['customer', 'sub_total', 'discount_percentage',
                                   'discount_amount', 'grand_total', 'amount_paid', 'items']
                for field in required_fields:
                    if field not in data or data[field] is None:
                        if field == 'discount_percentage' and data.get(field) == 0: # Allow explicit 0
                            continue
                        logger.error(f"SaleCreateView: Missing required field: {field}")
                        raise ValueError(f"Missing or null required field: {field}")

                customer_instance = Customer.objects.get(id=int(data['customer']))
                logger.info(f"SaleCreateView: Customer: {customer_instance.get_full_name()}, Initial total_due: {customer_instance.total_due}")


                form_grand_total = decimal.Decimal(data["grand_total"])
                form_amount_paid = decimal.Decimal(data["amount_paid"])
                calculated_amount_change = max(decimal.Decimal('0.00'), form_amount_paid - form_grand_total)
                logger.info(f"SaleCreateView: GT={form_grand_total}, AP={form_amount_paid}, CalculatedChange={calculated_amount_change}")


                sale_attributes = {
                    "customer": customer_instance,
                    "sub_total": decimal.Decimal(data["sub_total"]),
                    "discount_percentage": float(data["discount_percentage"]),
                    "discount_amount": decimal.Decimal(data["discount_amount"]),
                    "grand_total": form_grand_total,
                    "amount_paid": form_amount_paid,
                    "amount_change": calculated_amount_change,
                }

                with django_transaction.atomic():
                    new_sale = Sale.objects.create(**sale_attributes)
                    logger.info(f"SaleCreateView: Sale object created: ID {new_sale.id}")

                    items_data = data.get("items", [])
                    if not isinstance(items_data, list) or not items_data:
                        logger.error("SaleCreateView: Items data is invalid or empty.")
                        raise ValueError("Items should be a non-empty list.")

                    for item_data_dict in items_data:
                        if not all(k in item_data_dict for k in ["id", "price", "quantity", "total_item"]):
                            logger.error(f"SaleCreateView: Item data missing fields: {item_data_dict}")
                            raise ValueError(f"Item data is missing required fields: {item_data_dict}")
                        
                        item_instance = Item.objects.select_for_update().get(id=int(item_data_dict["id"]))
                        item_quantity_sold = int(item_data_dict["quantity"])
                        
                        if item_quantity_sold <= 0:
                            raise ValueError(f"Item quantity must be positive for item: {item_instance.name}")
                        if item_instance.quantity < item_quantity_sold:
                            raise ValueError(f"Not enough stock for item: {item_instance.name}. Available: {item_instance.quantity}, Requested: {item_quantity_sold}")

                        SaleDetail.objects.create(
                            sale=new_sale, item=item_instance,
                            price=decimal.Decimal(item_data_dict["price"]),
                            quantity=item_quantity_sold,
                            total_detail=decimal.Decimal(item_data_dict["total_item"])
                        )
                        item_instance.quantity -= item_quantity_sold
                        item_instance.save()
                        logger.info(f"SaleCreateView: Item {item_instance.name} stock updated to {item_instance.quantity}")

                    customer_instance_locked = Customer.objects.select_for_update().get(pk=customer_instance.pk)
                    current_sale_due_contribution = new_sale.amount_to_pay 
                    
                    original_customer_due = customer_instance_locked.total_due or decimal.Decimal('0.00')
                    customer_instance_locked.total_due = original_customer_due + current_sale_due_contribution
                    customer_instance_locked.save()
                    logger.info(f"SaleCreateView: Customer {customer_instance_locked.get_full_name()} total_due updated from {original_customer_due} to {customer_instance_locked.total_due} (added {current_sale_due_contribution})")

                messages.success(request, 'Sale created successfully!')
                return JsonResponse({'status': 'success', 'message': 'Sale created successfully!', 'redirect': reverse('saleslist')})

            except json.JSONDecodeError:
                logger.error("SaleCreateView: Invalid JSON format.", exc_info=True)
                return JsonResponse({'status': 'error', 'message': 'Invalid JSON format!'}, status=400)
            except (Customer.DoesNotExist, Item.DoesNotExist) as e:
                logger.error(f"SaleCreateView: Data integrity error - {e}", exc_info=True)
                return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            except ValueError as ve:
                logger.error(f"SaleCreateView: ValueError - {ve}", exc_info=True)
                return JsonResponse({'status': 'error', 'message': str(ve)}, status=400)
            except Exception as e:
                logger.error(f"SaleCreateView: Unexpected exception - {e}", exc_info=True)
                return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {str(e)}'}, status=500)
    return render(request, "transactions/sale_create.html", context=context)


@login_required
@user_passes_test(lambda u: u.is_staff) 
def SaleUpdateView(request, pk):
    sale_instance = get_object_or_404(Sale, pk=pk)

    if request.method == 'GET':
        sale_items_for_js = []
        for index, detail in enumerate(sale_instance.saledetail_set.all().select_related('item')):
            sale_items_for_js.append({
                'number': index + 1, 'id': detail.item.id, 'name': detail.item.name,
                'price': float(detail.price), 'quantity': detail.quantity,
                'total_item': float(detail.total_detail),
                'stock': detail.item.quantity + detail.quantity, # Stock available before this sale item was deducted
            })
        context = {
            "active_icon": "sales",
            "customers": [c.to_select2() for c in Customer.objects.all()],
            "sale_instance": sale_instance,
            "sale_items_json": json.dumps(sale_items_for_js),
            "form_action_url": reverse('sale-update', kwargs={'pk': pk}),
            "is_edit_mode": True, "title": f"Edit Sale #{sale_instance.id}"
        }
        return render(request, "transactions/sale_form_dynamic.html", context)

    elif request.method == 'POST':
        if is_ajax(request=request):
            try:
                data = json.loads(request.body)
                logger.info(f"SaleUpdateView POST data for Sale ID {pk}: {data}")

                required_fields = ['customer', 'sub_total', 'discount_percentage',
                                   'discount_amount', 'grand_total', 'amount_paid', 'items']
                for field in required_fields:
                    if field not in data or data[field] is None:
                        if field == 'discount_percentage' and data.get(field) == 0:
                            continue
                        logger.error(f"SaleUpdateView: Missing required field: {field}")
                        raise ValueError(f"Missing or null required field for update: {field}")

                new_customer_id = int(data['customer'])
                updated_items_data = data.get("items", [])
                if not isinstance(updated_items_data, list):
                    logger.error("SaleUpdateView: Updated items should be a list.")
                    raise ValueError("Updated items should be a list.")

                with django_transaction.atomic():
                    sale_to_update = Sale.objects.select_for_update().get(pk=pk)
                    original_customer = sale_to_update.customer
                    original_sale_due_contribution = sale_to_update.amount_to_pay 

                    logger.info(f"SaleUpdateView: Original Sale (ID {pk}) - Customer: {original_customer.get_full_name() if original_customer else 'None'}, Due Contribution: {original_sale_due_contribution}")

                    # Restock items from the original sale
                    for detail in sale_to_update.saledetail_set.all():
                        item = Item.objects.select_for_update().get(pk=detail.item_id)
                        item.quantity += detail.quantity
                        item.save()
                        logger.info(f"SaleUpdateView: Restocked {detail.quantity} of item '{item.name}' (ID: {item.id})")

                    # Revert customer due contribution from the original sale state
                    if original_customer: 
                        original_customer_locked = Customer.objects.select_for_update().get(pk=original_customer.pk)
                        original_customer_old_due = original_customer_locked.total_due or decimal.Decimal('0.00')
                        original_customer_locked.total_due = original_customer_old_due - original_sale_due_contribution
                        if original_customer_locked.total_due < decimal.Decimal('0.00'): # Ensure due does not go negative
                            original_customer_locked.total_due = decimal.Decimal('0.00')
                        original_customer_locked.save()
                        logger.info(f"SaleUpdateView: Reverted due for original customer {original_customer_locked.get_full_name()}. Old due: {original_customer_old_due}, New temp due: {original_customer_locked.total_due}")

                    # Delete old sale details
                    sale_to_update.saledetail_set.all().delete() 

                    # Update sale header fields
                    form_grand_total_update = decimal.Decimal(data["grand_total"])
                    form_amount_paid_update = decimal.Decimal(data["amount_paid"])
                    calculated_amount_change_update = max(decimal.Decimal('0.00'), form_amount_paid_update - form_grand_total_update)
                    logger.info(f"SaleUpdateView: New Sale Vals - GT={form_grand_total_update}, AP={form_amount_paid_update}, Change={calculated_amount_change_update}")

                    new_customer_instance = Customer.objects.get(id=new_customer_id) 
                    sale_to_update.customer = new_customer_instance
                    sale_to_update.sub_total = decimal.Decimal(data["sub_total"])
                    sale_to_update.discount_percentage = float(data["discount_percentage"])
                    sale_to_update.discount_amount = decimal.Decimal(data["discount_amount"])
                    sale_to_update.grand_total = form_grand_total_update
                    sale_to_update.amount_paid = form_amount_paid_update
                    sale_to_update.amount_change = calculated_amount_change_update
                    # Date_added remains the original sale date, not updated here
                    sale_to_update.save() # Save changes to sale header (including potentially new customer and financial figures)
                    logger.info(f"SaleUpdateView: Sale header updated for Sale ID: {sale_to_update.id}")

                    # Handle items if any, and check for consistency
                    if not updated_items_data and sale_to_update.sub_total > 0: # Or grand_total, depending on logic
                         raise ValueError("Cannot update sale to have a subtotal/grandtotal without items.")

                    # Create new sale details and deduct stock for new/updated items
                    for item_data_dict in updated_items_data:
                        if not all(k in item_data_dict for k in ["id", "price", "quantity", "total_item"]):
                             raise ValueError(f"Updated item data is missing required fields: {item_data_dict}")
                        
                        item_instance = Item.objects.select_for_update().get(id=int(item_data_dict["id"]))
                        item_quantity_sold = int(item_data_dict["quantity"])
                        
                        if item_quantity_sold <= 0:
                             raise ValueError(f"Item quantity must be positive for item: {item_instance.name}")
                        if item_instance.quantity < item_quantity_sold:
                            raise ValueError(f"Not enough stock for updated item: {item_instance.name}. Available: {item_instance.quantity}, Requested: {item_quantity_sold}")

                        SaleDetail.objects.create(
                            sale=sale_to_update, item=item_instance,
                            price=decimal.Decimal(item_data_dict["price"]),
                            quantity=item_quantity_sold,
                            total_detail=decimal.Decimal(item_data_dict["total_item"])
                        )
                        item_instance.quantity -= item_quantity_sold
                        item_instance.save()
                        logger.info(f"SaleUpdateView: Deducted {item_quantity_sold} of item '{item_instance.name}' (ID: {item_instance.id}) stock updated to {item_instance.quantity}")

                    # Apply new customer due contribution from the updated sale state
                    new_customer_locked = Customer.objects.select_for_update().get(pk=new_customer_instance.pk)
                    # sale_to_update.amount_to_pay will be calculated based on the NEWLY saved grand_total and amount_paid
                    current_sale_new_due_contribution = sale_to_update.amount_to_pay 
                    
                    new_customer_original_due = new_customer_locked.total_due or decimal.Decimal('0.00')
                    new_customer_locked.total_due = new_customer_original_due + current_sale_new_due_contribution
                    new_customer_locked.save()
                    logger.info(f"SaleUpdateView: Updated due for new/current customer {new_customer_locked.get_full_name()}. Due before this sale's new calc: {new_customer_original_due}, New total_due: {new_customer_locked.total_due} (added {current_sale_new_due_contribution})")

                messages.success(request, f'Sale #{sale_to_update.id} updated successfully!')
                return JsonResponse({'status': 'success', 'message': f'Sale #{sale_to_update.id} updated successfully!', 'redirect': reverse('saleslist')})

            except json.JSONDecodeError:
                logger.error("SaleUpdateView: Invalid JSON format.", exc_info=True)
                return JsonResponse({'status': 'error', 'message': 'Invalid JSON format!'}, status=400)
            except (Customer.DoesNotExist, Item.DoesNotExist) as e:
                logger.error(f"SaleUpdateView: Data integrity error - {e}", exc_info=True)
                return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
            except ValueError as ve:
                logger.error(f"SaleUpdateView: ValueError - {ve}", exc_info=True)
                return JsonResponse({'status': 'error', 'message': str(ve)}, status=400)
            except Exception as e:
                logger.error(f"SaleUpdateView: Unexpected exception for Sale ID {pk} - {e}", exc_info=True)
                return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {str(e)}'}, status=500)
        else: 
            return HttpResponse("This endpoint expects an AJAX POST request.", status=400)
    else: 
        return HttpResponse("Method not allowed.", status=405)


class SaleDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Sale
    template_name = "transactions/saledelete.html"

    def get_success_url(self):
        return reverse_lazy("saleslist")

    def test_func(self):
        # Allow staff or superuser to delete sales
        return self.request.user.is_staff

    @django_transaction.atomic
    def form_valid(self, form):
        sale_to_delete = self.get_object()
        logger.info(f"SaleDeleteView: Attempting to delete Sale ID {sale_to_delete.id}")
        logger.info(f"SaleDeleteView: Sale details - Customer: {sale_to_delete.customer}, GT: {sale_to_delete.grand_total}, AP: {sale_to_delete.amount_paid}")

        customer = sale_to_delete.customer

        # --- Customer Due Adjustment ---
        if customer:
            try:
                customer_locked = Customer.objects.select_for_update().get(pk=customer.pk)
                # amount_to_pay property calculates (grand_total - amount_paid) if GT > AP, else 0
                due_reduction_amount = sale_to_delete.amount_to_pay 

                original_customer_total_due = customer_locked.total_due or decimal.Decimal('0.00')
                customer_locked.total_due = original_customer_total_due - due_reduction_amount
                # Ensure total_due doesn't go negative from this operation
                customer_locked.total_due = max(decimal.Decimal('0.00'), customer_locked.total_due)
                customer_locked.save()
                logger.info(f"SaleDeleteView: Customer '{customer_locked.get_full_name()}' (ID: {customer_locked.pk}) total_due updated. Original: {original_customer_total_due}, Reduced by: {due_reduction_amount}, New total_due: {customer_locked.total_due}")
            except Customer.DoesNotExist:
                logger.error(f"SaleDeleteView: Customer with PK {customer.pk} for Sale ID {sale_to_delete.id} not found during due adjustment. Skipping due adjustment.")
        else:
            logger.info(f"SaleDeleteView: Sale ID {sale_to_delete.id} has no associated customer. No customer total_due adjustment applicable.")
        # --- End Customer Due Adjustment ---

        # Restock items (this logic remains)
        logger.info(f"SaleDeleteView: Proceeding to restock items for Sale ID {sale_to_delete.id}.")
        for detail in sale_to_delete.saledetail_set.all():
            try:
                item_to_restock = Item.objects.select_for_update().get(pk=detail.item.pk)
                original_stock = item_to_restock.quantity
                item_to_restock.quantity += detail.quantity
                item_to_restock.save()
                logger.info(f"SaleDeleteView: Restocked {detail.quantity} of item '{item_to_restock.name}' (ID: {item_to_restock.id}). Stock from {original_stock} to {item_to_restock.quantity}")
            except Item.DoesNotExist:
                logger.error(f"SaleDeleteView: Item with PK {detail.item.pk} for SaleDetail ID {detail.id} not found during restock. Skipping.")
                continue

        messages.success(self.request, f"Sale ID {sale_to_delete.id} has been successfully deleted. Items restocked and customer dues adjusted accordingly.")
        response = super().form_valid(form) # This performs the actual deletion of the Sale object
        logger.info(f"SaleDeleteView: Sale ID {sale_to_delete.id} successfully deleted from database.")
        return response

    def delete(self, request, *args, **kwargs):
        logger.info(f"SaleDeleteView: HTTP DELETE request for object PK {kwargs.get('pk')}")
        self.object = self.get_object() 
        return super().delete(request, *args, **kwargs)

# --- Purchase views ---
class PurchaseListView(LoginRequiredMixin, ListView):
    model = Purchase
    template_name = "transactions/purchases_list.html"
    context_object_name = "purchases"
    paginate_by = 10
    ordering = ['-order_date']

class PurchaseDetailView(LoginRequiredMixin, DetailView):
    model = Purchase
    template_name = "transactions/purchasedetail.html"

class PurchaseCreateView(LoginRequiredMixin, CreateView):
    model = Purchase
    form_class = PurchaseForm
    template_name = "transactions/purchases_form.html"
    def get_success_url(self):
        messages.success(self.request, "Purchase created successfully!")
        return reverse("purchaseslist")

class PurchaseUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    model = Purchase
    form_class = PurchaseForm
    template_name = "transactions/purchases_form.html"
    def test_func(self):
        return self.request.user.is_staff
    def get_success_url(self):
        messages.success(self.request, f"Purchase '{self.object}' updated successfully!")
        return reverse("purchaseslist")

class PurchaseDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Purchase
    template_name = "transactions/purchasedelete.html"
    def get_success_url(self):
        messages.success(self.request, f"Purchase '{self.object}' deleted successfully!")
        return reverse("purchaseslist")
    def test_func(self):
        return self.request.user.is_superuser

class SaleCustomerSearchView(LoginRequiredMixin,ListView):
    model = Sale
    template_name = "transactions/sales_list.html"
    context_object_name = "sales"
    paginate_by = 10 
    def get_queryset(self):
        queryset = super().get_queryset().select_related("customer").prefetch_related(
            Prefetch('saledetail_set', queryset=SaleDetail.objects.select_related('item'))
        )
        query = self.request.GET.get("q")
        if query:
            query_list = query.split()
            queryset = queryset.filter(
                reduce(operator.and_, (
                    Q(customer__first_name__icontains=q) |
                    Q(customer__last_name__icontains=q) |
                    Q(customer__email__icontains=q) |
                    Q(customer__phone__icontains=q)
                    for q in query_list
                ))
            )
        return queryset.order_by('-date_added')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['search_query'] = self.request.GET.get('q', '')
        return context