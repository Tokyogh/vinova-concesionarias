"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Shared role and route contract for deployment smoke tests.
"""

from __future__ import annotations

from dataclasses import dataclass

ROLE_CODES = [
    "superadmin",
    "admin_general",
    "admin_sucursal",
    "gerente_comercial",
    "jefe_inventario",
    "vendedor",
    "asesor_postventa",
    "facturacion",
    "bodega",
    "marketing",
    "soporte_cliente",
    "auditor",
    "cliente",
]

BRANCH_REQUIRED_ROLE_CODES = {
    "admin_sucursal",
    "jefe_inventario",
    "vendedor",
    "asesor_postventa",
    "facturacion",
    "bodega",
}

ROLE_PERMISSION_MAP = {
    "admin_general": {"*"},
    "superadmin": {"*"},
    "admin_sucursal": {
        "dashboard.view", "vehicles.view", "vehicles.manage", "vehicles.link_codes", "inventory.view", "inventory.manage_stock",
        "customers.view", "customers.manage", "sales.quote", "sales.reserve", "sales.sell", "invoices.view",
        "invoices.issue", "documents.view", "documents.manage", "documents.download_private", "notifications.view",
        "notifications.send", "notifications.manage_templates", "campaigns.view", "campaigns.manage",
        "campaigns.send", "reports.view", "imports.manage", "data.export",
        "leads.view", "leads.manage", "leads.assign", "leads.export", "analytics.view", "analytics.export",
        "privacy.view", "privacy.manage", "privacy.export", "help.view",
    },
    "gerente_comercial": {
        "dashboard.view", "vehicles.view", "customers.view", "sales.quote", "sales.reserve", "sales.sell",
        "invoices.view", "documents.view", "documents.download_private", "notifications.view", "notifications.send",
        "campaigns.view", "campaigns.manage", "campaigns.send",
        "reports.view", "leads.view", "leads.manage", "leads.assign", "leads.export", "analytics.view",
        "analytics.export", "help.view",
    },
    "jefe_inventario": {
        "dashboard.view", "vehicles.view", "vehicles.manage", "inventory.view", "inventory.manage_stock",
        "reports.view", "imports.manage", "data.export", "help.view",
    },
    "vendedor": {
        "dashboard.view", "vehicles.view", "customers.view", "customers.manage", "sales.quote", "sales.reserve",
        "documents.view", "notifications.view", "notifications.send", "leads.view", "leads.manage", "help.view",
    },
    "asesor_postventa": {
        "dashboard.view", "customers.view", "documents.view", "documents.download_private", "notifications.view",
        "notifications.send", "post_sales.view", "post_sales.manage", "help.view", "vehicles.link_codes",
    },
    "facturacion": {
        "dashboard.view", "sales.sell", "invoices.view", "invoices.issue", "invoices.manage", "invoices.void",
        "documents.view", "documents.manage", "documents.download_private", "notifications.view",
        "notifications.send", "help.view",
    },
    "bodega": {"dashboard.view", "inventory.view", "inventory.manage_stock", "help.view"},
    "marketing": {
        "dashboard.view", "vehicles.view", "vehicles.manage", "vehicles.publish", "customers.view",
        "notifications.view", "notifications.send", "notifications.manage_templates", "campaigns.view",
        "campaigns.manage", "campaigns.send", "imports.manage", "analytics.view", "help.view",
    },
    "soporte_cliente": {
        "dashboard.view", "customers.view", "documents.view", "notifications.view", "notifications.send",
        "leads.view", "leads.manage", "privacy.view", "privacy.manage", "help.view",
    },
    "auditor": {
        "dashboard.view", "vehicles.view", "inventory.view", "customers.view", "sales.quote", "invoices.view",
        "documents.view", "notifications.view", "reports.view", "data.export", "audit.view", "audit.export",
        "leads.view", "leads.export", "analytics.view", "analytics.export", "continuity.view", "privacy.view",
        "privacy.export", "security.view", "integrations.view", "quality.view", "help.view",
    },
    "cliente": {"portal.access"},
}

EXPECTED_DASHBOARD_PATH = {
    "superadmin": "/dashboard/admin/",
    "admin_general": "/dashboard/admin/",
    "admin_sucursal": "/dashboard/branch/",
    "gerente_comercial": "/dashboard/commercial/",
    "jefe_inventario": "/dashboard/inventory-home/",
    "vendedor": "/dashboard/seller/",
    "asesor_postventa": "/dashboard/support/",
    "facturacion": "/dashboard/billing/",
    "bodega": "/dashboard/inventory-home/",
    "marketing": "/dashboard/marketing/",
    "soporte_cliente": "/dashboard/support/",
    "auditor": "/dashboard/auditor/",
    "cliente": "/accounts/profile/",
}


@dataclass(frozen=True)
class RoleProbe:
    code: str
    label: str
    path: str
    permissions: tuple[str, ...]
    capability: str


PROBES = (
    RoleProbe("accounts.read", "Usuarios", "/accounts/users/", ("accounts.manage_users",), "GESTIONAR"),
    RoleProbe("accounts.create", "Crear usuario", "/accounts/users/new/", ("accounts.manage_users",), "GESTIONAR"),
    RoleProbe("companies", "Empresas", "/companies/", ("companies.manage",), "GESTIONAR"),
    RoleProbe("branches", "Sucursales", "/branches/", ("branches.manage",), "GESTIONAR"),
    RoleProbe("vehicles.read", "Vehículos", "/dashboard/vehicles/", ("vehicles.view", "vehicles.manage"), "LEER"),
    RoleProbe("vehicles.create", "Crear vehículo", "/dashboard/vehicles/new/", ("vehicles.manage",), "GESTIONAR"),
    RoleProbe("inventory.read", "Inventario", "/dashboard/inventory/", ("inventory.view", "inventory.manage_stock"), "LEER"),
    RoleProbe("inventory.create", "Crear artículo", "/dashboard/inventory/new/", ("inventory.manage_stock",), "GESTIONAR"),
    RoleProbe("customers.read", "Clientes", "/dashboard/customers/", ("customers.view", "customers.manage"), "LEER"),
    RoleProbe("customers.create", "Crear cliente", "/dashboard/customers/new/", ("customers.manage",), "GESTIONAR"),
    RoleProbe("sales.read", "Ventas", "/dashboard/sales/", ("sales.quote", "sales.reserve", "sales.sell"), "LEER"),
    RoleProbe("sales.create", "Crear venta/cotización", "/dashboard/sales/new/", ("sales.quote",), "GESTIONAR"),
    RoleProbe("invoices.read", "Facturación", "/dashboard/invoices/", ("invoices.view", "invoices.issue", "invoices.manage"), "LEER"),
    RoleProbe("invoices.issue", "Emitir factura", "/dashboard/invoices/new/", ("invoices.issue", "invoices.manage"), "GESTIONAR"),
    RoleProbe("documents.read", "Documentos", "/dashboard/documents/", ("documents.view", "documents.manage", "documents.download_private"), "LEER"),
    RoleProbe("documents.create", "Subir documento", "/dashboard/documents/upload/", ("documents.manage",), "GESTIONAR"),
    RoleProbe("notifications.read", "Notificaciones", "/dashboard/notifications/", ("notifications.view", "notifications.send"), "LEER"),
    RoleProbe("notifications.send", "Enviar notificación", "/dashboard/notifications/compose/", ("notifications.send",), "GESTIONAR"),
    RoleProbe("notifications.templates", "Plantillas", "/dashboard/notifications/templates/", ("notifications.manage_templates",), "GESTIONAR"),
    RoleProbe("reports", "Reportes", "/dashboard/reports/", ("reports.view",), "LEER"),
    RoleProbe("imports", "Importaciones", "/dashboard/imports/", ("imports.manage",), "GESTIONAR"),
    RoleProbe("leads.read", "CRM y leads", "/dashboard/leads/", ("leads.view", "leads.manage"), "LEER"),
    RoleProbe("leads.create", "Crear lead", "/dashboard/leads/new/", ("leads.manage",), "GESTIONAR"),
    RoleProbe("analytics", "Analítica", "/dashboard/analytics/", ("analytics.view",), "LEER"),
    RoleProbe("audit", "Auditoría", "/dashboard/audit/", ("audit.view",), "LEER"),
    RoleProbe("continuity", "Continuidad", "/dashboard/continuity/", ("continuity.view",), "LEER"),
    RoleProbe("privacy.read", "Privacidad", "/dashboard/privacy/", ("privacy.view",), "LEER"),
    RoleProbe("privacy.manage", "Gestionar privacidad", "/dashboard/privacy/requests/new/", ("privacy.manage",), "GESTIONAR"),
    RoleProbe("security.read", "Seguridad", "/dashboard/security/", ("security.view",), "LEER"),
    RoleProbe("security.manage", "Política de seguridad", "/dashboard/security/policy/", ("security.manage",), "GESTIONAR"),
    RoleProbe("integrations.read", "Integraciones", "/dashboard/integrations/", ("integrations.view", "integrations.manage"), "LEER"),
    RoleProbe("integrations.manage", "Crear cliente API", "/dashboard/integrations/clients/new/", ("integrations.manage",), "GESTIONAR"),
    RoleProbe("quality.read", "QA", "/dashboard/quality/", ("quality.view", "quality.run"), "LEER"),
    RoleProbe("help", "Centro de ayuda", "/dashboard/help/", ("help.view", "help.manage"), "LEER"),
    RoleProbe("enterprise", "Centro empresarial", "/dashboard/company/", ("enterprise.manage",), "GESTIONAR"),
    RoleProbe("sri", "Configuración SRI", "/dashboard/company/sri/", ("sri.manage",), "GESTIONAR"),
)


def expected_allowed(role_code: str, permissions: tuple[str, ...]) -> bool:
    role_permissions = ROLE_PERMISSION_MAP[role_code]
    return "*" in role_permissions or bool(role_permissions.intersection(permissions))
