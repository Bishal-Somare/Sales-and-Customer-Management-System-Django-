# Standard library imports
import json
import logging
import decimal # Import decimal

# Django core imports
from django.http import JsonResponse, HttpResponse
from django.urls import reverse, reverse_lazy 
from django.shortcuts import render, get_object_or_404
from django.db import transaction as django_transaction 
from django.db.models import Prefetch, Sum
from django.contrib.auth.decorators import login_required, user_passes_test 
from django.views.decorators.http import require_POST 

# Class-based views (some might still be used for other functionalities)
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView # UpdateView might be removed if not used

# Authentication and permissions
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

# Third-party packages
from openpyxl import Workbook
from django.contrib import messages 

# Local app imports
from store.models import Item
from accounts.models import Customer 
from .models import Sale, Purchase, SaleDetail
from .forms import PurchaseForm # SaleEditForm might be removed if not used by this view
from django.db.models import Q
from functools import reduce
import operator
from django.template.loader import render_to_string
import pdfkit


logger = logging.getLogger(__name__)

config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe') 

def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'

# --- PDF and Excel Export functions remain the same ---
def render_to_pdf(template_src, context_dict={}):
    html_content = render_to_string(template_src, context_dict)
    options = {
        'page-size': 'A4', 'encoding': 'UTF-8', 'enable-local-file-access': '',
        'no-outline': None, 'orientation' : 'landscape', 'margin-top': '5mm',
        'margin-right': '5mm', 'margin-bottom': '5mm', 'margin-left': '5mm',
        'zoom': '1.0', 'viewport-size': '1280x1024'
    }
    try:
        pdf = pdfkit.from_string(html_content, False, configuration=config, options=options)
        if pdf:
            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = 'inline; filename="report.pdf"'
            return response
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
    return HttpResponse("PDF generation failed. Please check server logs.", status=500)
   
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

# --- ListView and DetailView classes remain the same ---
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

# --- SaleCreateView remains the same ---
@login_required 
def SaleCreateView(request): 
    context = {
        "active_icon": "sales",
        "customers": [c.to_select2() for c in Customer.objects.all()]
    }
    if request.method == 'POST': # AJAX POST
        if is_ajax(request=request):
            try:
                data = json.loads(request.body)
                logger.info(f"Received data for sale creation: {data}")

                required_fields = ['customer', 'sub_total', 'discount_percentage', 
                                   'discount_amount', 'grand_total', 'amount_paid', 
                                   'amount_change', 'items']
                for field in required_fields:
                    if field not in data or data[field] is None:
                        if field == 'discount_percentage' and data.get(field) == 0:
                            continue
                        raise ValueError(f"Missing or null required field: {field}")

                customer_instance = Customer.objects.get(id=int(data['customer']))
                sale_attributes = {
                    "customer": customer_instance,
                    "sub_total": decimal.Decimal(data["sub_total"]),
                    "discount_percentage": float(data["discount_percentage"]),
                    "discount_amount": decimal.Decimal(data["discount_amount"]),
                    "grand_total": decimal.Decimal(data["grand_total"]),
                    "amount_paid": decimal.Decimal(data["amount_paid"]),
                    "amount_change": decimal.Decimal(data["amount_change"]),
                }

                with django_transaction.atomic():
                    new_sale = Sale.objects.create(**sale_attributes)
                    logger.info(f"Sale created: {new_sale}")

                    items_data = data.get("items", [])
                    if not isinstance(items_data, list):
                        raise ValueError("Items should be a list")
                    if not items_data:
                        raise ValueError("Cannot create a sale with no items.")

                    for item_data_dict in items_data: 
                        if not all(k in item_data_dict for k in ["id", "price", "quantity", "total_item"]):
                            raise ValueError(f"Item data is missing required fields: {item_data_dict}")
                        item_instance = Item.objects.get(id=int(item_data_dict["id"]))
                        item_quantity_sold = int(item_data_dict["quantity"]) 
                        if item_quantity_sold <= 0:
                            raise ValueError(f"Item quantity must be positive for item: {item_instance.name}")
                        if item_instance.quantity < item_quantity_sold:
                            raise ValueError(f"Not enough stock for item: {item_instance.name}. Available: {item_instance.quantity}, Requested: {item_quantity_sold}")
                        
                        detail_attributes = {
                            "sale": new_sale, "item": item_instance,
                            "price": decimal.Decimal(item_data_dict["price"]),
                            "quantity": item_quantity_sold,
                            "total_detail": decimal.Decimal(item_data_dict["total_item"])
                        }
                        SaleDetail.objects.create(**detail_attributes)
                        item_instance.quantity -= item_quantity_sold
                        item_instance.save()

                    current_sale_due = new_sale.amount_to_pay 
                    customer_instance.total_due = (customer_instance.total_due or decimal.Decimal('0.00')) + current_sale_due
                    customer_instance.save()
                    logger.info(f"Customer {customer_instance.get_full_name()}'s total_due updated to {customer_instance.total_due}")
                
                messages.success(request, 'Sale created successfully!')
                return JsonResponse({'status': 'success', 'message': 'Sale created successfully!', 'redirect': reverse('saleslist')})
            
            except json.JSONDecodeError:
                logger.error("Invalid JSON format received for sale creation.")
                return JsonResponse({'status': 'error', 'message': 'Invalid JSON format!'}, status=400)
            except Customer.DoesNotExist:
                logger.error(f"Customer not found during sale creation. Data: {data.get('customer')}")
                return JsonResponse({'status': 'error', 'message': 'Customer not found!'}, status=400)
            except Item.DoesNotExist:
                item_id_in_error = item_data_dict.get("id") if 'item_data_dict' in locals() else "unknown"
                logger.error(f"Item not found during sale creation. Item ID: {item_id_in_error}")
                return JsonResponse({'status': 'error', 'message': f'An item (ID: {item_id_in_error}) in the sale was not found!'}, status=400)
            except ValueError as ve:
                logger.error(f"ValueError during sale creation: {ve}")
                return JsonResponse({'status': 'error', 'message': str(ve)}, status=400)
            except TypeError as te:
                logger.error(f"TypeError during sale creation: {te}")
                return JsonResponse({'status': 'error', 'message': f'Invalid data type: {str(te)}'}, status=400)
            except Exception as e:
                logger.error(f"Unexpected exception during sale creation: {e}", exc_info=True)
                return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {str(e)}'}, status=500)
    return render(request, "transactions/sale_create.html", context=context) # GET request


# --- NEW/MODIFIED SaleUpdateView ---
@login_required
@user_passes_test(lambda u: u.is_staff) # Only staff can edit sales
def SaleUpdateView(request, pk):
    sale_instance = get_object_or_404(Sale, pk=pk)

    if request.method == 'GET':
        # Prepare data for the template, similar to SaleCreateView but with existing data
        sale_items_for_js = []
        for index, detail in enumerate(sale_instance.saledetail_set.all().select_related('item')):
            sale_items_for_js.append({
                'number': index + 1, # For display in the table row number
                'id': detail.item.id,
                'name': detail.item.name,
                'price': float(detail.price), # Ensure it's a float for JS
                'quantity': detail.quantity,
                'total_item': float(detail.total_detail),
                # Add other item properties if your JS expects them (e.g., stock, description)
                # 'stock': detail.item.quantity + detail.quantity, # Stock before this sale detail
            })
        
        context = {
            "active_icon": "sales",
            "customers": [c.to_select2() for c in Customer.objects.all()],
            "sale_instance": sale_instance, # Pass the whole instance
            "sale_items_json": json.dumps(sale_items_for_js), # Pass items as JSON for JS
            "form_action_url": reverse('sale-update', kwargs={'pk': pk}),
            "is_edit_mode": True,
            "title": f"Edit Sale #{sale_instance.id}"
        }
        return render(request, "transactions/sale_form_dynamic.html", context) # Use a new or adapted template

    elif request.method == 'POST': # AJAX POST
        if is_ajax(request=request):
            try:
                data = json.loads(request.body)
                logger.info(f"Received data for sale update (ID: {pk}): {data}")

                required_fields = ['customer', 'sub_total', 'discount_percentage', 
                                   'discount_amount', 'grand_total', 'amount_paid', 
                                   'amount_change', 'items']
                for field in required_fields:
                    if field not in data or data[field] is None:
                        if field == 'discount_percentage' and data.get(field) == 0:
                            continue
                        raise ValueError(f"Missing or null required field for update: {field}")

                new_customer_instance = Customer.objects.get(id=int(data['customer']))
                updated_items_data = data.get("items", [])
                if not isinstance(updated_items_data, list):
                    raise ValueError("Updated items should be a list.")
                # It's okay if updated_items_data is empty IF the intention is to remove all items,
                # but business logic might require at least one item. For now, allow empty.

                with django_transaction.atomic():
                    # 1. Lock the sale row for update
                    sale_to_update = Sale.objects.select_for_update().get(pk=pk)
                    original_customer = sale_to_update.customer
                    original_amount_to_pay = sale_to_update.amount_to_pay

                    # 2. Revert inventory for old SaleDetails & store old details
                    old_sale_details = list(sale_to_update.saledetail_set.all()) # Evaluate queryset
                    for detail in old_sale_details:
                        item = Item.objects.select_for_update().get(pk=detail.item_id)
                        item.quantity += detail.quantity
                        item.save()
                        logger.info(f"Sale Update: Restocked {detail.quantity} of item '{item.name}' (ID: {item.id}) from original sale {sale_to_update.id}")
                    
                    # 3. Revert original customer's total_due contribution from this sale
                    if original_customer:
                        original_customer.total_due = (original_customer.total_due or decimal.Decimal('0.00')) - original_amount_to_pay
                        if original_customer.total_due < decimal.Decimal('0.00'):
                            original_customer.total_due = decimal.Decimal('0.00')
                        original_customer.save()
                        logger.info(f"Sale Update: Customer {original_customer.get_full_name()} total_due reduced by {original_amount_to_pay} (old sale due). New total_due: {original_customer.total_due}")

                    # 4. Delete old SaleDetails
                    sale_to_update.saledetail_set.all().delete()

                    # 5. Update Sale header fields
                    sale_to_update.customer = new_customer_instance
                    sale_to_update.sub_total = decimal.Decimal(data["sub_total"])
                    sale_to_update.discount_percentage = float(data["discount_percentage"])
                    sale_to_update.discount_amount = decimal.Decimal(data["discount_amount"])
                    sale_to_update.grand_total = decimal.Decimal(data["grand_total"])
                    sale_to_update.amount_paid = decimal.Decimal(data["amount_paid"])
                    sale_to_update.amount_change = decimal.Decimal(data["amount_change"])
                    # date_added remains the same
                    sale_to_update.save() # Save updated sale header
                    logger.info(f"Sale header updated for Sale ID: {sale_to_update.id}")

                    # 6. Process new/updated SaleDetails and adjust inventory
                    if not updated_items_data and sale_to_update.sub_total > 0: # If subtotal > 0 means items were expected
                         raise ValueError("Cannot update sale to have a subtotal without items.")
                    
                    for item_data_dict in updated_items_data:
                        if not all(k in item_data_dict for k in ["id", "price", "quantity", "total_item"]):
                            raise ValueError(f"Updated item data is missing required fields: {item_data_dict}")
                        
                        item_instance = Item.objects.select_for_update().get(id=int(item_data_dict["id"]))
                        item_quantity_sold = int(item_data_dict["quantity"])
                        if item_quantity_sold <= 0:
                             raise ValueError(f"Item quantity must be positive for item: {item_instance.name}")

                        if item_instance.quantity < item_quantity_sold:
                            raise ValueError(f"Not enough stock for updated item: {item_instance.name}. Available: {item_instance.quantity}, Requested: {item_quantity_sold}")
                        
                        detail_attributes = {
                            "sale": sale_to_update, "item": item_instance,
                            "price": decimal.Decimal(item_data_dict["price"]),
                            "quantity": item_quantity_sold,
                            "total_detail": decimal.Decimal(item_data_dict["total_item"])
                        }
                        SaleDetail.objects.create(**detail_attributes)
                        item_instance.quantity -= item_quantity_sold
                        item_instance.save()
                        logger.info(f"Sale Update: Deducted {item_quantity_sold} of item '{item_instance.name}' (ID: {item_instance.id}) for updated sale {sale_to_update.id}")

                    # 7. Update new/current customer's total_due with the new sale's due amount
                    # sale_to_update is now refreshed with new details by this point, so amount_to_pay is correct
                    current_sale_due = sale_to_update.amount_to_pay 
                    new_customer_instance.total_due = (new_customer_instance.total_due or decimal.Decimal('0.00')) + current_sale_due
                    new_customer_instance.save()
                    logger.info(f"Sale Update: Customer {new_customer_instance.get_full_name()} total_due increased by {current_sale_due} (new sale due). New total_due: {new_customer_instance.total_due}")

                messages.success(request, f'Sale #{sale_to_update.id} updated successfully!')
                return JsonResponse({'status': 'success', 'message': f'Sale #{sale_to_update.id} updated successfully!', 'redirect': reverse('saleslist')})

            except json.JSONDecodeError:
                logger.error("Invalid JSON format received for sale update.")
                return JsonResponse({'status': 'error', 'message': 'Invalid JSON format!'}, status=400)
            except Customer.DoesNotExist:
                logger.error(f"Customer not found during sale update. Data: {data.get('customer')}")
                return JsonResponse({'status': 'error', 'message': 'Customer not found!'}, status=400)
            except Item.DoesNotExist:
                item_id_in_error = item_data_dict.get("id") if 'item_data_dict' in locals() else "unknown"
                logger.error(f"Item not found during sale update. Item ID: {item_id_in_error}")
                return JsonResponse({'status': 'error', 'message': f'An item (ID: {item_id_in_error}) in the sale was not found!'}, status=400)
            except ValueError as ve:
                logger.error(f"ValueError during sale update: {ve}")
                return JsonResponse({'status': 'error', 'message': str(ve)}, status=400)
            except TypeError as te: # Often from Decimal conversion if data is malformed
                logger.error(f"TypeError during sale update: {te}")
                return JsonResponse({'status': 'error', 'message': f'Invalid data type: {str(te)}'}, status=400)
            except Exception as e:
                logger.error(f"Unexpected exception during sale update (ID: {pk}): {e}", exc_info=True)
                return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {str(e)}'}, status=500)
        else: # Not AJAX
            return HttpResponse("This endpoint expects an AJAX POST request.", status=400)
    else: # Other methods
        return HttpResponse("Method not allowed.", status=405)


# --- SaleDeleteView remains mostly the same, ensure logging and messages ---
class SaleDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Sale
    template_name = "transactions/saledelete.html"
    
    def get_success_url(self):
        # messages.success(self.request, f"Sale ID {self.object.id} has been successfully deleted.") # Message now in form_valid
        return reverse_lazy("saleslist")
    
    def test_func(self):
        return self.request.user.is_superuser 

    @django_transaction.atomic
    def form_valid(self, form):
        sale_to_delete = self.get_object()
        customer = sale_to_delete.customer
        sale_due_amount = sale_to_delete.amount_to_pay
        
        # Revert customer's total_due
        if customer and customer.total_due is not None and sale_due_amount is not None:
            customer.total_due = (customer.total_due or decimal.Decimal('0.00')) - sale_due_amount
            if customer.total_due < decimal.Decimal('0.00'):
                customer.total_due = decimal.Decimal('0.00')
            customer.save()
            logger.info(f"Customer {customer.get_full_name()}'s total_due reduced by {sale_due_amount} to {customer.total_due} after deleting Sale ID {sale_to_delete.id}")

        # Restock items
        for detail in sale_to_delete.saledetail_set.all():
            item = detail.item
            item.quantity += detail.quantity
            item.save()
            logger.info(f"Restocked {detail.quantity} of item '{item.name}' (ID: {item.id}) after deleting Sale ID {sale_to_delete.id}")
        
        messages.success(self.request, f"Sale ID {sale_to_delete.id} has been successfully deleted.")
        return super().form_valid(form)

# --- Purchase views remain the same ---
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