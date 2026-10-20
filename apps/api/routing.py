"""ES: Este módulo implementa el componente routing para el dominio de API e integraciones.

EN: This module implements the routing component for the api domain.

Contexto existente / Existing context:
Routing support for the api domain.
"""

from rest_framework.routers import DefaultRouter

from apps.accounts.api.views import RoleViewSet, UserViewSet
from apps.analytics.api.views import VehicleInteractionViewSet
from apps.api.views import (
    APIClientViewSet,
    APIScopeViewSet,
    IntegrationLogViewSet,
    WebhookDeliveryViewSet,
    WebhookEndpointViewSet,
    WebhookEventViewSet,
)
from apps.audit.api.views import AuditLogViewSet, SecurityAlertViewSet
from apps.branches.api.views import BranchViewSet
from apps.companies.api.views import CompanyViewSet
from apps.continuity.api.views import BackupPolicyViewSet, BackupRecordViewSet, RestoreDrillViewSet
from apps.customers.api.views import CustomerNoteViewSet, CustomerVehicleInterestViewSet, CustomerViewSet
from apps.documents.api.views import DocumentCategoryViewSet, PrivateDocumentViewSet, ReusableAssetViewSet
from apps.enterprise.api.views import ApprovalPolicyViewSet, CompanyPublicSettingsViewSet
from apps.imports.api.views import ImportBatchViewSet, ImportRowViewSet
from apps.inventory.api.views import BranchStockViewSet, InventoryCategoryViewSet, InventoryItemViewSet, StockMovementViewSet
from apps.invoices.api.views import (
    InvoiceLineViewSet,
    InvoicePaymentApplicationViewSet,
    InvoiceRecordViewSet,
    InvoiceSequenceViewSet,
    InvoiceStatusHistoryViewSet,
)
from apps.leads.api.views import LeadActivityViewSet, LeadViewSet, TestDriveViewSet
from apps.notifications.api.views import NotificationMessageViewSet, NotificationRecipientViewSet, NotificationTemplateViewSet
from apps.privacy.api.views import ConsentRecordViewSet, DataExportJobViewSet, DataSubjectRequestViewSet, RetentionPolicyViewSet
from apps.sales.api.views import SaleLineViewSet, SalePaymentViewSet, SaleRecordViewSet, SaleStatusHistoryViewSet
from apps.security_center.api.views import ActiveSessionViewSet, SecurityPolicyViewSet
from apps.sri_integration.api.views import SriConfigurationViewSet, SriEstablishmentViewSet, SriSequenceViewSet
from apps.vehicles.api.views import VehicleViewSet


def build_router():
    router = DefaultRouter()
    router.register("users", UserViewSet, basename="users")
    router.register("roles", RoleViewSet, basename="roles")
    router.register("audit-logs", AuditLogViewSet, basename="audit-logs")
    router.register("backup-policies", BackupPolicyViewSet, basename="backup-policies")
    router.register("backups", BackupRecordViewSet, basename="backups")
    router.register("restore-drills", RestoreDrillViewSet, basename="restore-drills")
    router.register("privacy-consents", ConsentRecordViewSet, basename="privacy-consents")
    router.register("security-policies", SecurityPolicyViewSet, basename="security-policies")
    router.register("security-sessions", ActiveSessionViewSet, basename="security-sessions")
    router.register("data-subject-requests", DataSubjectRequestViewSet, basename="data-subject-requests")
    router.register("data-exports", DataExportJobViewSet, basename="data-exports")
    router.register("retention-policies", RetentionPolicyViewSet, basename="retention-policies")
    router.register("security-alerts", SecurityAlertViewSet, basename="security-alerts")
    router.register("leads", LeadViewSet, basename="leads")
    router.register("lead-activities", LeadActivityViewSet, basename="lead-activities")
    router.register("test-drives", TestDriveViewSet, basename="test-drives")
    router.register("vehicle-interactions", VehicleInteractionViewSet, basename="vehicle-interactions")
    router.register("companies", CompanyViewSet, basename="companies")
    router.register("branches", BranchViewSet, basename="branches")
    router.register("vehicles", VehicleViewSet, basename="vehicles")
    router.register("customers", CustomerViewSet, basename="customers")
    router.register("customer-notes", CustomerNoteViewSet, basename="customer-notes")
    router.register("customer-interests", CustomerVehicleInterestViewSet, basename="customer-interests")
    router.register("inventory-categories", InventoryCategoryViewSet, basename="inventory-categories")
    router.register("inventory-items", InventoryItemViewSet, basename="inventory-items")
    router.register("inventory-stock", BranchStockViewSet, basename="inventory-stock")
    router.register("inventory-movements", StockMovementViewSet, basename="inventory-movements")
    router.register("sales", SaleRecordViewSet, basename="sales")
    router.register("sale-lines", SaleLineViewSet, basename="sale-lines")
    router.register("sale-payments", SalePaymentViewSet, basename="sale-payments")
    router.register("sale-status-history", SaleStatusHistoryViewSet, basename="sale-status-history")
    router.register("document-categories", DocumentCategoryViewSet, basename="document-categories")
    router.register("documents", PrivateDocumentViewSet, basename="documents")
    router.register("reusable-assets", ReusableAssetViewSet, basename="reusable-assets")
    router.register("notification-messages", NotificationMessageViewSet, basename="notification-messages")
    router.register("notification-recipients", NotificationRecipientViewSet, basename="notification-recipients")
    router.register("notification-templates", NotificationTemplateViewSet, basename="notification-templates")
    router.register("invoices", InvoiceRecordViewSet, basename="invoices")
    router.register("invoice-lines", InvoiceLineViewSet, basename="invoice-lines")
    router.register("invoice-payments", InvoicePaymentApplicationViewSet, basename="invoice-payments")
    router.register("invoice-sequences", InvoiceSequenceViewSet, basename="invoice-sequences")
    router.register("invoice-status-history", InvoiceStatusHistoryViewSet, basename="invoice-status-history")
    router.register("company-public-settings", CompanyPublicSettingsViewSet, basename="company-public-settings")
    router.register("approval-policies", ApprovalPolicyViewSet, basename="approval-policies")
    router.register("sri-configurations", SriConfigurationViewSet, basename="sri-configurations")
    router.register("sri-establishments", SriEstablishmentViewSet, basename="sri-establishments")
    router.register("sri-sequences", SriSequenceViewSet, basename="sri-sequences")
    router.register("imports", ImportBatchViewSet, basename="imports")
    router.register("import-rows", ImportRowViewSet, basename="import-rows")
    router.register("api-scopes", APIScopeViewSet, basename="api-scopes")
    router.register("api-clients", APIClientViewSet, basename="api-clients")
    router.register("webhook-endpoints", WebhookEndpointViewSet, basename="webhook-endpoints")
    router.register("webhook-events", WebhookEventViewSet, basename="webhook-events")
    router.register("webhook-deliveries", WebhookDeliveryViewSet, basename="webhook-deliveries")
    router.register("integration-logs", IntegrationLogViewSet, basename="integration-logs")
    return router
