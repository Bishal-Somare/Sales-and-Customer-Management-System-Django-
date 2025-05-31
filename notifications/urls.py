from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('send-due-reminders/', views.send_due_reminder_page, name='send_due_reminders_page'),
    path('get-customer-due-amount/<int:customer_id>/', views.get_customer_due_amount_ajax, name='get_customer_due_amount_ajax'),
    # The email sending actions will be handled by send_due_reminder_page via POST
    path('settings/', views.notify_settings_page, name='notify_settings_page'),
    path('record-partial-payment/', views.record_partial_payment_ajax, name='record_partial_payment_ajax'), 
    path('customer-dues/', views.customer_due_list_view, name='customer_due_list'), # customer ko due list
]