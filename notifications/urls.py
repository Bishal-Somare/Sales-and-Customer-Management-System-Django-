# notifications/urls.py
from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('send-due-reminders/', views.send_due_reminder_page, name='send_due_reminders_page'),
    path('get-customer-due-amount/<int:customer_id>/', views.get_customer_due_amount_ajax, name='get_customer_due_amount_ajax'),
    path('settings/', views.notify_settings_page, name='notify_settings_page'),
    path('record-partial-payment/', views.record_partial_payment_ajax, name='record_partial_payment_ajax'), 
    path('customer-dues/', views.customer_due_list_view, name='customer_due_list'),

    # --- NEW URLS ---
    path('get-cached/', views.get_cached_notifications_view, name='get_cached_notifications'),
    # Ensure notification_id can contain underscores and periods from timestamp
    path('dismiss/<str:notification_id>/', views.dismiss_notification_view, name='dismiss_notification'), 
]