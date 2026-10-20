"""ES: Este módulo declara el enrutamiento URL para el dominio de paneles.

EN: This module declares URL routing for the dashboard domain.

Contexto existente / Existing context:
URL routing for the dashboard domain.
"""

from django.urls import path

from apps.dashboard.views import (
    AdminDashboardView,
    AuditorDashboardView,
    BillingDashboardView,
    BranchDashboardView,
    CommercialDashboardView,
    DashboardRouterView,
    InventoryDashboardView,
    MarketingDashboardView,
    PublicAboutView,
    PublicHomeView,
    PublicServicesView,
    SellerDashboardView,
    StaffDashboardView,
    SupportDashboardView,
    WorkerDashboardView,
    dashboard_preferences,
    assist_query,
    universal_search,
)

app_name = "dashboard"

urlpatterns = [
    path("", PublicHomeView.as_view(), name="home"),
    path("servicios/", PublicServicesView.as_view(), name="services"),
    path("nosotros/", PublicAboutView.as_view(), name="about"),
    path("dashboard/", DashboardRouterView.as_view(), name="staff_home"),
    path("dashboard/admin/", AdminDashboardView.as_view(), name="admin_home"),
    path("dashboard/branch/", BranchDashboardView.as_view(), name="branch_home"),
    path("dashboard/commercial/", CommercialDashboardView.as_view(), name="commercial_home"),
    path("dashboard/seller/", SellerDashboardView.as_view(), name="seller_home"),
    path("dashboard/inventory-home/", InventoryDashboardView.as_view(), name="inventory_home"),
    path("dashboard/billing/", BillingDashboardView.as_view(), name="billing_home"),
    path("dashboard/support/", SupportDashboardView.as_view(), name="support_home"),
    path("dashboard/marketing/", MarketingDashboardView.as_view(), name="marketing_home"),
    path("dashboard/auditor/", AuditorDashboardView.as_view(), name="auditor_home"),
    path("dashboard/worker/", WorkerDashboardView.as_view(), name="worker_home"),
    path("dashboard/preferences/", dashboard_preferences, name="preferences"),
    path("dashboard/assist/", assist_query, name="assist"),
    path("dashboard/search/", universal_search, name="universal_search"),
    path("dashboard/internal/", StaffDashboardView.as_view(), name="internal_home_legacy"),
]
