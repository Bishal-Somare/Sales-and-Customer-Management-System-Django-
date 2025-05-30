# Django core imports
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static

# Local app imports
from .views import (
    PurchaseListView, PurchaseDetailView, PurchaseCreateView,
    PurchaseUpdateView, PurchaseDeleteView, SaleListView,
    SaleDetailView, SaleCreateView, SaleUpdateView, SaleDeleteView, # SaleUpdateView is now the function

    export_sales_to_excel, export_purchases_to_excel,
    export_sales_to_pdf, export_detailed_sales_to_pdf,
    SaleCustomerSearchView,
)

# URL patterns
urlpatterns = [
    # Purchase URLs
    path('purchases/', PurchaseListView.as_view(), name='purchaseslist'),
    path('purchase/<slug:slug>/', PurchaseDetailView.as_view(), name='purchase-detail'),
    path('new-purchase/', PurchaseCreateView.as_view(), name='purchase-create'),
    path('purchase/<int:pk>/update/', PurchaseUpdateView.as_view(), name='purchase-update'),
    path('purchase/<int:pk>/delete/', PurchaseDeleteView.as_view(), name='purchase-delete'),

    # Sale URLs
    path('sales/', SaleListView.as_view(), name='saleslist'),
    path('sale/<int:pk>/', SaleDetailView.as_view(), name='sale-detail'),
    path('new-sale/', SaleCreateView, name='sale-create'), 
    path('sale/<int:pk>/edit/', SaleUpdateView, name='sale-update'), # Points to the function view
    path('sale/<int:pk>/delete/', SaleDeleteView.as_view(), name='sale-delete'),
    
    # Sales and purchases export
    path('sales/export/', export_sales_to_excel, name='sales-export'),
    path('purchases/export/', export_purchases_to_excel, name='purchases-export'),
    path('sales/export-pdf/', export_sales_to_pdf, name='sales-export-pdf'),
    path('sales/<int:pk>/export-detailed-pdf/', export_detailed_sales_to_pdf, name='sales-export-detailed-pdf'),
    path("sales/search/", SaleCustomerSearchView.as_view(), name="sale_search")
]

# Static media files configuration for development
if settings.DEBUG: 
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)