"""ES: Este módulo declara el enrutamiento URL para el dominio de configuración.

EN: This module declares URL routing for the configuration domain.

Contexto existente / Existing context:
Vinova runtime configuration for urls.
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

from apps.analytics.views import CustomerExecutiveProfileView, UserCommercialProfileView
from apps.api.docs import VinovaSpectacularAPIView, VinovaSpectacularSwaggerView
from apps.common.health import dependencies, live, ready

urlpatterns = [
    path("health/live/", live, name="health-live"),
    path("health/ready/", ready, name="health-ready"),
    path("health/dependencies/", dependencies, name="health-dependencies"),
    path("admin/", admin.site.urls),
    path("", include("apps.dashboard.urls")),
    path("instituciones/", include("apps.branches.public_urls")),
    path("repuestos/", include("apps.inventory.public_urls")),
    path("accounts/", include("apps.accounts.urls")),
    path("mi-cuenta/", include("apps.portal.urls")),
    path("", include("apps.security_center.urls")),
    path("companies/", include("apps.companies.urls")),
    path("branches/", include("apps.branches.urls")),
    path("vehicles/", include("apps.vehicles.urls")),
    path("leads/", include("apps.leads.urls")),
    path("privacy/", include("apps.privacy.public_urls")),
    path(
        "vehiculos/",
        RedirectView.as_view(pattern_name="vehicles:catalog", permanent=False),
        name="vehiculos_public_redirect",
    ),
    path("dashboard/vehicles/", include("apps.vehicles.internal_urls")),
    path(
        "dashboard/customers/<int:pk>/profile/",
        CustomerExecutiveProfileView.as_view(),
        name="analytics_customer_profile",
    ),
    path("dashboard/users/<int:pk>/profile/", UserCommercialProfileView.as_view(), name="analytics_user_profile"),
    path("dashboard/customers/", include("apps.customers.urls")),
    path("dashboard/inventory/", include("apps.inventory.urls")),
    path("dashboard/sales/", include("apps.sales.urls")),
    path("dashboard/documents/", include("apps.documents.urls")),
    path("dashboard/invoices/", include("apps.invoices.urls")),
    path("dashboard/notifications/", include("apps.notifications.urls")),
    path("dashboard/reports/", include("apps.reports.urls")),
    path("dashboard/leads/", include("apps.leads.internal_urls")),
    path("dashboard/analytics/", include("apps.analytics.urls")),
    path("dashboard/audit/", include("apps.audit.urls")),
    path("dashboard/continuity/", include("apps.continuity.urls")),
    path("dashboard/privacy/", include("apps.privacy.urls")),
    path("dashboard/imports/", include("apps.imports.urls")),
    path("dashboard/company/", include("apps.enterprise.urls")),
    path("dashboard/company/sri/", include("apps.sri_integration.urls")),
    path("dashboard/integrations/", include("apps.api.internal_urls")),
    path("dashboard/help/", include("apps.help_center.urls")),
    path("dashboard/quality/", include("apps.quality.urls")),
    path("dashboard/post-sales/", include("apps.post_sales.urls")),
    path("dashboard/", include("apps.common.urls")),
    path("api/schema/", VinovaSpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", VinovaSpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path(
        "api/v1/schema/",
        VinovaSpectacularAPIView.as_view(urlconf="apps.api.schema_urls"),
        name="schema-v1",
    ),
    path("api/v1/docs/", VinovaSpectacularSwaggerView.as_view(url_name="schema-v1"), name="swagger-ui-v1"),
    path("api/v1/", include("apps.api.v1_urls")),
    path("api/", include("apps.api.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
