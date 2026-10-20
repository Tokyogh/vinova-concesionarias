"""ES: Este módulo declara el enrutamiento URL para el dominio de facturación.

EN: This module declares URL routing for the invoices domain.

Contexto existente / Existing context:
URL routing for the invoices domain.
"""

from django.urls import path

from apps.invoices.views import InvoiceActionView, InvoiceCreateFromSaleView, InvoiceDetailView, InvoiceLineCreateView, InvoiceListView, InvoicePaymentApplyView, InvoicePdfDownloadView, InvoicePrintView

app_name = "invoices_internal"

urlpatterns = [
    path("", InvoiceListView.as_view(), name="list"),
    path("new/", InvoiceCreateFromSaleView.as_view(), name="create_from_sale"),
    path("<int:pk>/", InvoiceDetailView.as_view(), name="detail"),
    path("<int:pk>/print/", InvoicePrintView.as_view(), name="print"),
    path("<int:pk>/pdf/", InvoicePdfDownloadView.as_view(), name="pdf_download"),
    path("<int:pk>/lines/new/", InvoiceLineCreateView.as_view(), name="line_create"),
    path("<int:pk>/payments/apply/", InvoicePaymentApplyView.as_view(), name="payment_apply"),
    path("<int:pk>/action/<slug:action>/", InvoiceActionView.as_view(), name="action"),
]
