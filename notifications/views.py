# notifications/views.py
import json
import decimal
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.core.mail import send_mail, get_connection, EmailMessage
from django.template.loader import render_to_string
from django.conf import settings
from django.views.decorators.http import require_POST, require_GET
from django.db import transaction as django_transaction
import logging

from accounts.models import Customer
from django.contrib.auth.decorators import login_required
# from transactions.models import Sale # Not directly used in these functions anymore for due calculation

logger = logging.getLogger(__name__)

def _get_customer_total_due(customer):
    # It's good practice to refresh if the customer object might be stale,
    # though select_for_update in the calling function also helps.
    customer.refresh_from_db()
    return customer.total_due if customer.total_due is not None else decimal.Decimal('0.00')

@require_GET
def get_customer_due_amount_ajax(request, customer_id):
    if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request type.'}, status=400)
    try:
        customer = get_object_or_404(Customer, pk=customer_id)
        total_due = customer.total_due if customer.total_due is not None else decimal.Decimal('0.00')
        logger.info(f"AJAX get_customer_due_amount: Customer ID {customer_id}, Name: {customer.get_full_name()}, Due from DB: {total_due}")
        return JsonResponse({
            'customer_name': customer.get_full_name(),
            'due_amount': str(total_due.quantize(decimal.Decimal('0.01')))
        })
    except Exception as e:
        logger.error(f"Error in get_customer_due_amount_ajax for Customer ID {customer_id}: {e}", exc_info=True)
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def send_due_reminder_page(request):
    if request.method == 'GET':
        customers = Customer.objects.all().order_by('first_name', 'last_name')
        context = {
            'customers': customers,
        }
        return render(request, 'notifications/send_due_reminders.html', context)

    elif request.method == 'POST':
        if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'error': 'Invalid request type for POST.'}, status=400)

        try:
            data = json.loads(request.body)
            action = data.get('action')
            logger.info(f"send_due_reminder_page POST: Action: {action}, Data: {data}")


            if action == 'send_single':
                customer_id = data.get('customer_id')
                if not customer_id:
                    return JsonResponse({'error': 'Customer ID is required.'}, status=400)

                customer = get_object_or_404(Customer, pk=customer_id)
                amount_due = _get_customer_total_due(customer) # Refreshes customer from DB

                if amount_due <= 0:
                    logger.info(f"Send Single Reminder: Customer {customer.get_full_name()} has no dues (Due: {amount_due}). Email not sent.")
                    return JsonResponse({'message': f'{customer.get_full_name()} has no outstanding balance.', 'status': 'info'})

                if not customer.email:
                    logger.warning(f"Send Single Reminder: Customer {customer.get_full_name()} has no email. Email not sent.")
                    return JsonResponse({'error': f'{customer.get_full_name()} does not have an email address configured.'}, status=400)

                email_context = {
                    'customer_name': customer.get_full_name(),
                    'amount_due': amount_due.quantize(decimal.Decimal('0.01'))
                }
                subject = render_to_string('notifications/email/due_reminder_subject.txt', email_context).strip()
                html_body = render_to_string('notifications/email/due_reminder_body.html', email_context)

                try:
                    send_mail(
                        subject, '', settings.EMAIL_HOST_USER, [customer.email],
                        html_message=html_body, fail_silently=False,
                    )
                    logger.info(f"Send Single Reminder: Email sent successfully to {customer.get_full_name()} for due {amount_due}.")
                    return JsonResponse({'message': f'Email sent successfully to {customer.get_full_name()}.', 'status': 'success'})
                except Exception as e:
                    logger.error(f"Send Single Reminder: Failed to send email to {customer.get_full_name()}: {e}", exc_info=True)
                    return JsonResponse({'error': f'Failed to send email to {customer.get_full_name()}: {str(e)}'}, status=500)

            elif action == 'send_all':
                customers_with_any_debt = Customer.objects.filter(total_due__gt=decimal.Decimal('0.00')).distinct()
                logger.info(f"Send All Reminders: Found {customers_with_any_debt.count()} customers with dues.")


                if not customers_with_any_debt.exists():
                     return JsonResponse({'message': 'No customers found with outstanding payments.', 'status': 'info'})

                email_messages = []
                successfully_queued_customers = []
                failed_customers = []

                for customer_obj in customers_with_any_debt:
                    amount_due = customer_obj.total_due # Already filtered, so this should be > 0
                    if customer_obj.email:
                        email_context = {
                            'customer_name': customer_obj.get_full_name(),
                            'amount_due': amount_due.quantize(decimal.Decimal('0.01'))
                        }
                        subject = render_to_string('notifications/email/due_reminder_subject.txt', email_context).strip()
                        html_body = render_to_string('notifications/email/due_reminder_body.html', email_context)
                        msg = EmailMessage(subject, html_body, settings.EMAIL_HOST_USER, [customer_obj.email])
                        msg.content_subtype = "html"
                        email_messages.append(msg)
                        successfully_queued_customers.append(customer_obj.get_full_name())
                    else:
                        failed_customers.append(f"{customer_obj.get_full_name()} (no email)")
                        logger.warning(f"Send All Reminders: Customer {customer_obj.get_full_name()} has dues but no email.")


                if not email_messages:
                    msg = 'No emails could be prepared.'
                    if failed_customers:
                         msg += f' Issues: {", ".join(failed_customers)}'
                    logger.info(f"Send All Reminders: {msg}")
                    return JsonResponse({'message': msg, 'status': 'warning' if failed_customers else 'info'})

                try:
                    connection = get_connection(fail_silently=False)
                    connection.open()
                    num_sent = connection.send_messages(email_messages)
                    connection.close()

                    response_message = f'{num_sent} emails sent successfully to: {", ".join(successfully_queued_customers)}.'
                    if failed_customers:
                        response_message += f' Could not send to: {", ".join(failed_customers)}.'
                    logger.info(f"Send All Reminders: Batch send result - {response_message}")
                    return JsonResponse({'message': response_message, 'status': 'success', 'sent_count': num_sent})
                except Exception as e:
                    logger.error(f"Send All Reminders: Error during batch email sending: {e}", exc_info=True)
                    return JsonResponse({'error': f'Error during batch email sending: {str(e)}'}, status=500)
            else:
                logger.warning(f"send_due_reminder_page POST: Invalid action '{action}'.")
                return JsonResponse({'error': 'Invalid action.'}, status=400)

        except json.JSONDecodeError:
            logger.error("send_due_reminder_page POST: Invalid JSON data.", exc_info=True)
            return JsonResponse({'error': 'Invalid JSON data.'}, status=400)
        except Exception as e:
            logger.error(f'send_due_reminder_page POST: An unexpected error occurred: {e}', exc_info=True)
            return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)

    return JsonResponse({'error': 'Method not allowed.'}, status=405)


@login_required
@require_POST
def record_partial_payment_ajax(request):
    if not request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'error': 'Invalid request type.'}, status=400)

    try:
        data = json.loads(request.body)
        customer_id = data.get('customer_id')
        payment_amount_str = data.get('payment_amount')
        logger.info(f"Record Payment AJAX: Received data: customer_id={customer_id}, payment_amount='{payment_amount_str}'")


        if not customer_id or not payment_amount_str:
            logger.warning("Record Payment: Customer ID or payment amount missing from request.")
            return JsonResponse({'error': 'Customer ID and payment amount are required.'}, status=400)

        try:
            payment_amount = decimal.Decimal(payment_amount_str)
        except decimal.InvalidOperation:
            logger.warning(f"Record Payment: Invalid payment amount format '{payment_amount_str}' for customer ID {customer_id}.")
            return JsonResponse({'error': 'Invalid payment amount format.'}, status=400)

        if payment_amount <= 0:
            logger.warning(f"Record Payment: Non-positive payment amount '{payment_amount}' for customer ID {customer_id}.")
            return JsonResponse({'error': 'Payment amount must be positive.'}, status=400)

        with django_transaction.atomic():
            # Lock the customer row for update
            customer_locked = Customer.objects.select_for_update().get(pk=customer_id)
            current_due_before_payment = customer_locked.total_due if customer_locked.total_due is not None else decimal.Decimal('0.00')
            logger.info(f"Record Payment: Customer ID {customer_id}, Name: {customer_locked.get_full_name()}, Due Before: {current_due_before_payment}, Payment Received: {payment_amount}")

            if payment_amount > current_due_before_payment:
                logger.warning(f"Record Payment: Payment amount {payment_amount} exceeds due amount {current_due_before_payment} for customer ID {customer_id}.")
                return JsonResponse({
                    'error': f'Payment amount (Rs. {payment_amount.quantize(decimal.Decimal("0.01"))}) cannot exceed the due amount (Rs. {current_due_before_payment.quantize(decimal.Decimal("0.01"))}).'
                }, status=400)

            customer_locked.total_due -= payment_amount
            if customer_locked.total_due < decimal.Decimal('0.00'): # Ensure not negative
                customer_locked.total_due = decimal.Decimal('0.00')
            customer_locked.save()

            # Verify the save by re-fetching (optional, but good for robust logging)
            # customer_after_save = Customer.objects.get(pk=customer_id)
            # new_due_after_payment = customer_after_save.total_due
            # The customer_locked instance should be up-to-date after .save() within the same transaction.
            new_due_after_payment = customer_locked.total_due
            logger.info(f"Record Payment: Customer ID {customer_id}, Due After Save (from locked instance): {new_due_after_payment}")

        return JsonResponse({
            'status': 'success',
            'message': f'Payment of Rs. {payment_amount.quantize(decimal.Decimal("0.01"))} recorded successfully for {customer_locked.get_full_name()}.',
            'new_due_amount': str(new_due_after_payment.quantize(decimal.Decimal('0.01')))
        })

    except json.JSONDecodeError:
        logger.error("Record Payment AJAX: Invalid JSON data.", exc_info=True)
        return JsonResponse({'error': 'Invalid JSON data.'}, status=400)
    except Customer.DoesNotExist:
        logger.warning(f"Record Payment AJAX: Customer with ID {data.get('customer_id')} not found.")
        return JsonResponse({'error': 'Customer not found.'}, status=404)
    except Exception as e:
        logger.error(f"Record Payment AJAX: Error for customer_id={data.get('customer_id') if 'data' in locals() else 'unknown'}: {e}", exc_info=True)
        return JsonResponse({'error': f'An unexpected error occurred: {str(e)}'}, status=500)


@login_required
def notify_settings_page(request):
    context = {'active_icon': 'notification_settings'}
    return render(request, 'notifications/notify_setting.html', context)

@login_required
def customer_due_list_view(request):
    logger.info("--- Entering customer_due_list_view ---")

    # Initial queryset based on the filter
    customers_with_dues_qs = Customer.objects.filter(total_due__gt=decimal.Decimal('0.00')).order_by('first_name', 'last_name')
    logger.info(f"Customer Due List: Initial queryset count based on total_due > 0: {customers_with_dues_qs.count()}")

    customers_to_display = []
    if customers_with_dues_qs.exists(): # Optimization: only loop if there are potential candidates
        for customer_in_qs in customers_with_dues_qs:
            # FOR DEBUGGING: Re-fetch the customer individually
            try:
                # Using refresh_from_db() on the existing instance from queryset
                # This is slightly more efficient than Customer.objects.get() if the instance is already loaded
                # but for ultimate certainty of a fresh read for debugging, .get() is fine too.
                customer_in_qs.refresh_from_db(fields=['total_due']) # Only refresh total_due
                
                logger.info(f"Customer Due List: Processing Customer: {customer_in_qs.get_full_name()} (ID: {customer_in_qs.pk}), Refreshed DB total_due: {customer_in_qs.total_due}")

                if customer_in_qs.total_due is not None and customer_in_qs.total_due > decimal.Decimal('0.00'):
                    customers_to_display.append(customer_in_qs) # Add the (potentially refreshed) instance
                    logger.info(f"  -> ADDING to display list. Name: {customer_in_qs.get_full_name()}, Due: {customer_in_qs.total_due}")
                else:
                    logger.info(f"  -> SKIPPING from display list because refreshed total_due is {customer_in_qs.total_due}. Name: {customer_in_qs.get_full_name()}")
            except Customer.DoesNotExist: # Should not happen if iterating queryset
                logger.error(f"Customer Due List: Customer with PK {customer_in_qs.pk} from initial queryset not found when re-fetching. This is very odd.")
                continue
    else:
        logger.info("Customer Due List: Initial queryset was empty. No customers to process.")


    logger.info(f"Customer Due List: Final count of customers to display after individual checks: {len(customers_to_display)}")

    context = {
        'customers_with_dues': customers_to_display,
        'active_icon': 'customer_dues',
    }
    return render(request, 'notifications/customer_due_list.html', context)