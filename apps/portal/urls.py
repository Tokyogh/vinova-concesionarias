"""ES: Este módulo declara el enrutamiento URL para el dominio de portal cliente.

EN: This module declares URL routing for the portal domain.

Contexto existente / Existing context:
URL routing for the portal domain.
"""

from django.urls import path

from apps.portal.views import (
    PortalDashboardView,
    PortalDocumentListView,
    PortalInvoiceDetailView,
    PortalInvoiceDownloadView,
    PortalInvoiceListView,
    PortalNotificationArchiveView,
    PortalNotificationDetailView,
    PortalNotificationListView,
    PortalNotificationReadAllView,
    PortalManualDownloadView,
    PortalPrivateDocumentDetailView,
    PortalPrivateDocumentDownloadView,
    PortalProfileView,
    PortalSettingsView,
    PortalServiceDetailView,
    PortalServiceListView,
    PortalVehicleDetailView,
    PortalVehicleListView,
    PortalVehicleRedeemView,
)

app_name = "portal"

urlpatterns = [
    path("", PortalDashboardView.as_view(), name="dashboard"),
    path("perfil/", PortalProfileView.as_view(), name="profile"),
    path("configuracion/", PortalSettingsView.as_view(), name="settings"),
    path("vehiculos/", PortalVehicleListView.as_view(), name="vehicle_list"),
    path("vehiculos/agregar/", PortalVehicleRedeemView.as_view(), name="vehicle_redeem"),
    path("vehiculos/<int:pk>/", PortalVehicleDetailView.as_view(), name="vehicle_detail"),
    path("documentos/", PortalDocumentListView.as_view(), name="document_list"),
    path("documentos/<int:pk>/", PortalPrivateDocumentDetailView.as_view(), name="document_detail"),
    path("documentos/<int:pk>/descargar/", PortalPrivateDocumentDownloadView.as_view(), name="document_download"),
    path("manuales/<int:pk>/descargar/", PortalManualDownloadView.as_view(), name="manual_download"),
    path("facturas/", PortalInvoiceListView.as_view(), name="invoice_list"),
    path("facturas/<int:pk>/", PortalInvoiceDetailView.as_view(), name="invoice_detail"),
    path("facturas/<int:pk>/descargar/", PortalInvoiceDownloadView.as_view(), name="invoice_download"),
    path("notificaciones/", PortalNotificationListView.as_view(), name="notification_list"),
    path("notificaciones/marcar-todas/", PortalNotificationReadAllView.as_view(), name="notification_read_all"),
    path("notificaciones/<int:pk>/", PortalNotificationDetailView.as_view(), name="notification_detail"),
    path("notificaciones/<int:pk>/archivar/", PortalNotificationArchiveView.as_view(), name="notification_archive"),
    path("servicios/", PortalServiceListView.as_view(), name="service_list"),
    path("servicios/<int:pk>/", PortalServiceDetailView.as_view(), name="service_detail"),
]
