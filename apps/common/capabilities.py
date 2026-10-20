"""ES: Este módulo implementa el componente capabilities para el dominio de infraestructura compartida.

EN: This module implements the capabilities component for the common domain.

Contexto existente / Existing context:
Capabilities support for the common domain.
"""

from __future__ import annotations


CAPABILITY_PERMISSION_CODES = {
    "can_view_internal_vehicles": ("vehicles.view", "vehicles.manage"),
    "can_manage_vehicles": ("vehicles.manage",),
    "can_view_customers": ("customers.view", "customers.manage"),
    "can_manage_customers": ("customers.manage",),
    "can_view_leads": ("leads.view",),
    "can_access_sales": ("sales.quote", "sales.reserve", "sales.sell"),
    "can_manage_quotes": ("sales.quote",),
    "can_view_inventory": ("inventory.view", "inventory.manage_stock"),
    "can_view_documents": ("documents.view", "documents.manage", "documents.download_private"),
    "can_manage_documents": ("documents.manage",),
    "can_view_invoices": ("invoices.view", "invoices.issue", "invoices.manage"),
    "can_issue_invoices": ("invoices.issue", "invoices.manage"),
    "can_view_notifications": ("notifications.view", "notifications.send"),
    "can_view_reports": ("reports.view",),
    "can_view_analytics": ("analytics.view",),
    "can_manage_imports": ("imports.manage",),
    "can_view_integrations": ("integrations.view", "integrations.manage"),
    "can_manage_enterprise_settings": ("enterprise.manage",),
    "can_manage_companies": ("companies.manage",),
    "can_manage_branches": ("branches.manage",),
    "can_manage_users": ("accounts.manage_users",),
    "can_view_audit": ("audit.view",),
    "can_view_continuity": ("continuity.view",),
    "can_view_privacy": ("privacy.view",),
    "can_view_security": ("security.view",),
    "can_view_quality": ("quality.view", "quality.run"),
    "can_view_help": ("help.view", "help.manage"),
    "can_view_post_sales": ("post_sales.view", "post_sales.manage"),
}

DIRECT_ATTRIBUTE_PERMISSIONS = object()


def permission_codes_for_user(user):
    """Snapshot de permisos vigentes: una consulta para roles, ninguna para superuser."""
    if getattr(user, "is_superuser", False):
        return None
    if not hasattr(user, "active_role_assignments"):
        return DIRECT_ATTRIBUTE_PERMISSIONS
    return set(user.active_role_assignments().values_list("role__permissions__code", flat=True).distinct())


def allows_capability(capability: str | None, user, permission_codes) -> bool:
    if not capability:
        return True
    if permission_codes is None:
        return True
    if permission_codes is DIRECT_ATTRIBUTE_PERMISSIONS:
        return bool(getattr(user, capability, False))
    expected = CAPABILITY_PERMISSION_CODES.get(capability)
    if expected is not None:
        return bool(permission_codes.intersection(expected))
    return bool(getattr(user, capability, False))
