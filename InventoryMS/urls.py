from django.contrib import admin
from django.urls import path, include,re_path
from accounts import views

#custom
handler404 = 'accounts.views.custom_404_view'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('store.urls')),
    path('staff/', include('accounts.urls')),
    path('transactions/', include('transactions.urls')),
    path('accounts/', include('accounts.urls')),
    path('invoice/', include('invoice.urls')),
    path('bills/', include('bills.urls')),
    # re_path(r'^.*$', views.custom_404_view),  # this catches any non-matched URL
    #for notifications
    path('notifications/', include('notifications.urls', namespace='notifications')),
    

]
admin.site.site_header='GanaSalesLite'
admin.site.site_title='GanasalesLite'


