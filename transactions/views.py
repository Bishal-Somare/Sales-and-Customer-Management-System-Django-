# Standard library imports
import json
import logging
import decimal # Import decimal

# Django core imports
from django.http import JsonResponse, HttpResponse
from django.urls import reverse
from django.shortcuts import render, get_object_or_404
from django.db import transaction as django_transaction 
from django.db.models import Prefetch, Sum
from django.contrib.auth.decorators import login_required 
from django.views.decorators.http import require_POST 

# Class-based views
from django.views.generic import DetailView, ListView
from django.views.generic.edit import CreateView, UpdateView, DeleteView

# Authentication and permissions
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin

# Third-party packages
from openpyxl import Workbook

# Local app imports
from store.models import Item
from accounts.models import Customer 
from .models import Sale, Purchase, SaleDetail
from .forms import PurchaseForm
from django.db.models import Q
from functools import reduce
import operator
from django.http import HttpResponse
from django.template.loader import render_to_string
import pdfkit


logger = logging.getLogger(__name__)

config = pdfkit.configuration(wkhtmltopdf=r'C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe') 

def is_ajax(request):
    return request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'


def render_to_pdf(template_src, context_dict={}):
    html_content = render_to_string(template_src, context_dict)
    options = {
        'page-size': 'A4', 'encoding': 'UTF-8', 'enable-local-file-access': '',
        'no-outline': None, 'orientation' : 'landscape', 'margin-top': '5mm',
        'margin-right': '5mm', 'margin-bottom': '5mm', 'margin-left': '5mm',
        'zoom': '1.0', 'viewport-size': '1280x1024'
    }
    pdf = pdfkit.from_string(html_content, False, configuration=config, options=options)
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="report.pdf"'
        return response
    return HttpResponse("PDF generation failed")
   

def export_detailed_sales_to_pdf(request, pk):
    sale = get_object_or_404(
        Sale.objects.select_related('customer').prefetch_related(
            Prefetch('saledetail_set', queryset=SaleDetail.objects.select_related('item'))
        ), id=pk
    )
    context = {'sale': sale}
    return render_to_pdf('transactions/sale_ticket.html', context)
    
def export_sales_to_pdf(request):
    sales = Sale.objects.all()
    context = {'sales': sales}
    # The sales_table.html template is used for PDF export, so changes there will reflect here.
    pdf = render_to_pdf('transactions/sales_table.html', context) 
    if pdf:
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename="sales_report.pdf"'
        return response
    logger.error("PDF generation failed.")
    return HttpResponse("PDF generation failed.")

def export_sales_to_excel(request):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = 'Sales'
    columns = [
        'ID', 'Date', 'Customer', 'Items', 'Sub Total', 'Discount %', 'Discount Amount',
        'Grand Total', 
        'Amount Paid', 
        # 'Amount to Pay (This Sale)', # Removed from Excel export header
        'Amount Change'
    ]
    worksheet.append(columns)
    sales = Sale.objects.all().prefetch_related('saledetail_set__item', 'customer') # Added customer prefetch
    for sale in sales:
        # Ensure customer phone is accessed correctly; assuming customer.phone exists
        customer_identifier = sale.customer.phone if sale.customer and sale.customer.phone else sale.customer.get_full_name()
        date_added = sale.date_added.replace(tzinfo=None) if sale.date_added.tzinfo else sale.date_added
        worksheet.append([
            sale.id, date_added, customer_identifier, sale.get_items_display(),
            sale.sub_total, sale.discount_percentage, sale.discount_amount,
            sale.grand_total, 
            sale.amount_paid, 
            # sale.amount_to_pay, # Removed from data row
            sale.amount_change
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
    purchases = Purchase.objects.all()
    for purchase in purchases:
        delivery_date = purchase.delivery_date.replace(tzinfo=None) if purchase.delivery_date and purchase.delivery_date.tzinfo else purchase.delivery_date
        order_date = purchase.order_date.replace(tzinfo=None) if purchase.order_date.tzinfo else purchase.order_date
        worksheet.append([
            purchase.id, purchase.item.name, purchase.description, purchase.vendor.name,
            order_date, delivery_date, purchase.quantity, 
            purchase.get_delivery_status_display(), purchase.price, purchase.total_value
        ])
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=purchases.xlsx'
    workbook.save(response)
    return response


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
                logger.info(f"Received data for sale creation: {data}")

                required_fields = [
                    'customer', 'sub_total', 'discount_percentage', 'discount_amount',
                    'grand_total', 'amount_paid', 'amount_change', 'items'
                ]
                for field in required_fields:
                    if field not in data or data[field] is None: 
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

                    items = data["items"]
                    if not isinstance(items, list):
                        raise ValueError("Items should be a list")

                    for item_data in items: 
                        if not all(k in item_data for k in ["id", "price", "quantity", "total_item"]):
                            raise ValueError("Item is missing required fields")

                        item_instance = Item.objects.get(id=int(item_data["id"]))
                        item_quantity_sold = int(item_data["quantity"]) 

                        if item_instance.quantity < item_quantity_sold:
                            raise ValueError(f"Not enough stock for item: {item_instance.name}. Available: {item_instance.quantity}, Requested: {item_quantity_sold}")

                        detail_attributes = {
                            "sale": new_sale,
                            "item": item_instance,
                            "price": decimal.Decimal(item_data["price"]),
                            "quantity": item_quantity_sold,
                            "total_detail": decimal.Decimal(item_data["total_item"])
                        }
                        SaleDetail.objects.create(**detail_attributes)
                        logger.info(f"Sale detail created: {detail_attributes}")

                        item_instance.quantity -= item_quantity_sold
                        item_instance.save()

                    current_sale_due = new_sale.amount_to_pay 
                    customer_total_due_before_update = customer_instance.total_due if customer_instance.total_due is not None else decimal.Decimal('0.00')
                    customer_instance.total_due = customer_total_due_before_update + current_sale_due
                    customer_instance.save()
                    logger.info(f"Customer {customer_instance.get_full_name()}'s total_due updated to {customer_instance.total_due}")


                return JsonResponse({'status': 'success', 'message': 'Sale created successfully!', 'redirect': reverse('saleslist')})
            except json.JSONDecodeError:
                return JsonResponse({'status': 'error', 'message': 'Invalid JSON format!'}, status=400)
            except Customer.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Customer not found!'}, status=400)
            except Item.DoesNotExist:
                return JsonResponse({'status': 'error', 'message': 'Item not found!'}, status=400)
            except ValueError as ve:
                logger.error(f"ValueError during sale creation: {ve}")
                return JsonResponse({'status': 'error', 'message': str(ve)}, status=400)
            except TypeError as te:
                logger.error(f"TypeError during sale creation: {te}")
                return JsonResponse({'status': 'error', 'message': str(te)}, status=400)
            except Exception as e:
                logger.error(f"Unexpected exception during sale creation: {e}", exc_info=True)
                return JsonResponse({'status': 'error', 'message': f'An unexpected error occurred: {str(e)}'}, status=500)
    return render(request, "transactions/sale_create.html", context=context)


class SaleDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Sale
    template_name = "transactions/saledelete.html"
    
    def get_success_url(self):
        return reverse("saleslist")
    
    def test_func(self):
        return self.request.user.is_superuser

    @django_transaction.atomic
    def form_valid(self, form):
        sale_to_delete = self.get_object()
        customer = sale_to_delete.customer
        
        sale_due_amount = sale_to_delete.amount_to_pay
        
        if customer.total_due is not None and sale_due_amount is not None:
            customer.total_due -= sale_due_amount
            if customer.total_due < decimal.Decimal('0.00'):
                customer.total_due = decimal.Decimal('0.00')
            customer.save()
            logger.info(f"Customer {customer.get_full_name()}'s total_due reduced by {sale_due_amount} to {customer.total_due} after deleting Sale ID {sale_to_delete.id}")

        for detail in sale_to_delete.saledetail_set.all():
            item = detail.item
            item.quantity += detail.quantity
            item.save()
            logger.info(f"Restocked {detail.quantity} of item '{item.name}' after deleting Sale ID {sale_to_delete.id}")
            
        return super().form_valid(form)


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
        return reverse("purchaseslist")


class PurchaseUpdateView(LoginRequiredMixin, UpdateView):
    model = Purchase
    form_class = PurchaseForm
    template_name = "transactions/purchases_form.html"
    def get_success_url(self):
        return reverse("purchaseslist")


class PurchaseDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    model = Purchase
    template_name = "transactions/purchasedelete.html"
    def get_success_url(self):
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
                    Q(customer__email__icontains=q)
                    for q in query_list
                ))
            )
        return queryset.order_by('-date_added')