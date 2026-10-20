"""ES: Este módulo implementa servicios de negocio y efectos transaccionales para el dominio de paneles.

EN: This module implements business services and transactional effects for the dashboard domain.

Contexto existente / Existing context:
Transactional business services for the dashboard domain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable, Mapping, Sequence

from django.urls import reverse

from apps.common.modules import is_module_enabled


@dataclass(frozen=True)
class DashboardProfile:
    code: str
    name: str
    url_name: str
    description: str


@dataclass(frozen=True)
class DashboardWidget:
    """Declarative dashboard block; access is always checked server-side."""

    key: str
    title: str
    description: str
    permissions: tuple[str, ...] = field(default_factory=tuple)
    module: str | None = None


@dataclass(frozen=True)
class DashboardAction:
    key: str
    title: str
    description: str
    url_name: str
    permissions: tuple[str, ...] = field(default_factory=tuple)
    module: str | None = None


@dataclass(frozen=True)
class DashboardManifest:
    profile: DashboardProfile
    widgets: tuple[DashboardWidget, ...]
    actions: tuple[dict, ...]
    permission_codes: frozenset[str]


DASHBOARD_PROFILES = {
    "admin": DashboardProfile(
        code="admin",
        name="Administración general",
        url_name="dashboard:admin_home",
        description="Control global de empresa, staff, sucursales, operación y seguridad.",
    ),
    "branch": DashboardProfile(
        code="branch",
        name="Administración de sucursal",
        url_name="dashboard:branch_home",
        description="Gestión diaria de una concesionaria, bodega o centro de atención.",
    ),
    "commercial": DashboardProfile(
        code="commercial",
        name="Gerencia comercial",
        url_name="dashboard:commercial_home",
        description="Seguimiento comercial, oportunidades, reservas y ventas.",
    ),
    "seller": DashboardProfile(
        code="seller",
        name="Ventas y atención",
        url_name="dashboard:seller_home",
        description="Trabajo diario de asesores, clientes, cotizaciones y reservas.",
    ),
    "inventory": DashboardProfile(
        code="inventory",
        name="Inventario y bodega",
        url_name="dashboard:inventory_home",
        description="Control de artículos, stock, movimientos y alertas por sucursal.",
    ),
    "billing": DashboardProfile(
        code="billing",
        name="Facturación y documentos",
        url_name="dashboard:billing_home",
        description="Ventas listas para facturar, pagos, comprobantes y documentación privada.",
    ),
    "support": DashboardProfile(
        code="support",
        name="Atención al cliente",
        url_name="dashboard:support_home",
        description="Clientes, postventa, documentos y comunicaciones internas.",
    ),
    "marketing": DashboardProfile(
        code="marketing",
        name="Catálogo y marketing",
        url_name="dashboard:marketing_home",
        description="Contenido comercial, vehículos publicables, multimedia y recursos reutilizables.",
    ),
    "auditor": DashboardProfile(
        code="auditor",
        name="Auditoría y lectura",
        url_name="dashboard:auditor_home",
        description="Vista controlada de operaciones, documentos, reportes y trazabilidad.",
    ),
    "worker": DashboardProfile(
        code="worker",
        name="Panel operativo",
        url_name="dashboard:worker_home",
        description="Panel interno mínimo ajustado a los permisos disponibles.",
    ),
    "client": DashboardProfile(
        code="client",
        name="Panel de usuario",
        url_name="accounts:profile",
        description="Experiencia privada de usuario/cliente, separada de la operación interna.",
    ),
}


ADMIN_ROLE_CODES = {"superadmin", "admin_general"}
BRANCH_ROLE_CODES = {"admin_sucursal"}
COMMERCIAL_ROLE_CODES = {"gerente_comercial"}
SELLER_ROLE_CODES = {"vendedor"}
INVENTORY_ROLE_CODES = {"jefe_inventario", "bodega"}
BILLING_ROLE_CODES = {"facturacion"}
SUPPORT_ROLE_CODES = {"asesor_postventa", "soporte_cliente"}
MARKETING_ROLE_CODES = {"marketing"}
AUDITOR_ROLE_CODES = {"auditor"}
CLIENT_ROLE_CODES = {"cliente"}


ROLE_PRIORITY = [
    ("admin", ADMIN_ROLE_CODES),
    ("branch", BRANCH_ROLE_CODES),
    ("commercial", COMMERCIAL_ROLE_CODES),
    ("seller", SELLER_ROLE_CODES),
    ("inventory", INVENTORY_ROLE_CODES),
    ("billing", BILLING_ROLE_CODES),
    ("support", SUPPORT_ROLE_CODES),
    ("marketing", MARKETING_ROLE_CODES),
    ("auditor", AUDITOR_ROLE_CODES),
    ("client", CLIENT_ROLE_CODES),
]


PROFILE_PERMISSION_PRIORITY = (
    ("admin", ("accounts.manage_users", "companies.manage", "branches.manage", "enterprise.manage")),
    ("branch", ("branches.manage",)),
    ("commercial", ("sales.sell", "analytics.view", "leads.assign")),
    ("seller", ("sales.quote", "sales.reserve")),
    ("inventory", ("inventory.view", "inventory.manage_stock")),
    ("billing", ("invoices.view", "invoices.issue", "invoices.manage", "documents.manage")),
    ("support", ("post_sales.view", "post_sales.manage", "notifications.send")),
    ("marketing", ("vehicles.publish", "campaigns.manage", "campaigns.send")),
    ("auditor", ("audit.view", "reports.view", "quality.view")),
)


DASHBOARD_WIDGETS = (
    DashboardWidget(
        "sales",
        "Rendimiento comercial",
        "Cotizaciones, reservas, ventas e ingresos dentro de tu alcance.",
        ("sales.quote", "sales.reserve", "sales.sell"),
    ),
    DashboardWidget(
        "leads",
        "Pipeline y seguimiento",
        "Oportunidades activas y seguimientos pendientes autorizados.",
        ("leads.view", "leads.manage"),
    ),
    DashboardWidget(
        "inventory",
        "Inventario",
        "Stock disponible, alertas y movimientos de las sucursales accesibles.",
        ("inventory.view", "inventory.manage_stock"),
    ),
    DashboardWidget(
        "invoices",
        "Facturación",
        "Comprobantes y valores del periodo dentro de tu alcance.",
        ("invoices.view", "invoices.issue", "invoices.manage"),
    ),
    DashboardWidget(
        "customers",
        "Clientes",
        "Cartera y actividad reciente de clientes autorizados.",
        ("customers.view", "customers.manage"),
    ),
    DashboardWidget(
        "tasks",
        "Prioridades",
        "Pendientes reales que requieren atención.",
        (
            "sales.quote",
            "sales.reserve",
            "sales.sell",
            "leads.view",
            "leads.manage",
            "inventory.view",
            "inventory.manage_stock",
            "invoices.view",
            "invoices.issue",
            "invoices.manage",
            "notifications.view",
            "audit.view",
        ),
    ),
    DashboardWidget(
        "activity",
        "Actividad reciente",
        "Cambios recientes visibles según permisos y alcance.",
        (
            "sales.quote",
            "sales.reserve",
            "sales.sell",
            "leads.view",
            "leads.manage",
            "inventory.view",
            "inventory.manage_stock",
            "invoices.view",
            "documents.view",
            "documents.manage",
        ),
    ),
)


DASHBOARD_ACTIONS = (
    DashboardAction(
        "new_customer", "Registrar cliente", "Crear un cliente dentro de tu alcance.",
        "customers_internal:create", ("customers.manage",),
    ),
    DashboardAction(
        "new_lead", "Registrar lead", "Añadir una oportunidad al pipeline.",
        "leads_internal:create", ("leads.manage",),
    ),
    DashboardAction(
        "new_quote", "Nueva cotización", "Iniciar una operación comercial.",
        "sales_internal:create", ("sales.quote",),
    ),
    DashboardAction(
        "new_vehicle", "Registrar vehículo", "Añadir una unidad al inventario vehicular.",
        "vehicles_internal:create", ("vehicles.manage",),
    ),
    DashboardAction(
        "new_stock_item", "Registrar artículo", "Crear un artículo de inventario.",
        "inventory_internal:create", ("inventory.manage_stock",),
    ),
    DashboardAction(
        "stock_movement", "Movimiento de stock", "Registrar una entrada o salida de inventario.",
        "inventory_internal:movement_create", ("inventory.manage_stock",),
    ),
    DashboardAction(
        "new_invoice", "Crear comprobante", "Facturar una operación autorizada.",
        "invoices_internal:create_from_sale", ("invoices.issue", "invoices.manage"),
    ),
    DashboardAction(
        "upload_document", "Registrar documento", "Cargar documentación privada autorizada.",
        "documents_internal:create", ("documents.manage",),
    ),
    DashboardAction(
        "compose_message", "Enviar notificación", "Redactar una comunicación interna.",
        "notifications_internal:compose", ("notifications.send",),
    ),
)


def _active_access(user) -> tuple[set[str], set[str]]:
    """Load role and permission codes in one query each for the whole dashboard."""

    if not getattr(user, "is_authenticated", False):
        return set(), set()
    assignments = user.active_role_assignments()
    roles = set(assignments.values_list("role__code", flat=True).distinct())
    permissions = set(assignments.values_list("role__permissions__code", flat=True).distinct())
    return roles, permissions


def _has_any(user, granted: set[str], required: Iterable[str]) -> bool:
    required = tuple(required)
    return bool(getattr(user, "is_superuser", False) or not required or granted.intersection(required))


def _module_available(module: str | None, user, granted: set[str]) -> bool:
    if module is None:
        return True
    return is_module_enabled(module) and _has_any(user, granted, (f"{module}.view", f"{module}.manage"))


def _safe_order(items: Sequence, requested: object) -> tuple:
    """Apply a preference only to the already-authorized registry subset."""

    by_key = {item.key: item for item in items}
    keys = requested if isinstance(requested, (list, tuple)) else ()
    ordered = [by_key.pop(key) for key in keys if isinstance(key, str) and key in by_key]
    ordered.extend(item for item in items if item.key in by_key)
    return tuple(ordered)


def dashboard_manifest_for_user(user, preferences: Mapping | None = None) -> DashboardManifest:
    """Resolve profile, widgets and actions from real access, then apply safe ordering."""

    preferences = preferences if isinstance(preferences, Mapping) else {}
    _roles, permissions = _active_access(user)
    profile = dashboard_profile_for_user(user, role_codes=_roles, permission_codes=permissions)

    widgets = tuple(
        item
        for item in DASHBOARD_WIDGETS
        if _has_any(user, permissions, item.permissions) and _module_available(item.module, user, permissions)
    )
    actions = tuple(
        item
        for item in DASHBOARD_ACTIONS
        if _has_any(user, permissions, item.permissions) and _module_available(item.module, user, permissions)
    )
    widgets = _safe_order(widgets, preferences.get("widget_order"))
    actions = _safe_order(actions, preferences.get("action_order"))
    resolved_actions = tuple(
        {
            "key": item.key,
            "title": item.title,
            "description": item.description,
            "url": reverse(item.url_name),
        }
        for item in actions
    )
    return DashboardManifest(
        profile=profile,
        widgets=widgets,
        actions=resolved_actions,
        permission_codes=frozenset(permissions),
    )


def dashboard_profile_for_user(
    user,
    *,
    role_codes: set[str] | None = None,
    permission_codes: set[str] | None = None,
) -> DashboardProfile:
    """Return the dashboard experience that best fits the user's active roles.

    Vinova Pro intentionally does not expose a single generic dashboard to every
    role. Users can hold several roles, so the highest-impact business profile is
    selected first. Module access is still enforced by permissions in each view;
    this function only chooses the landing experience.
    """

    if not getattr(user, "is_authenticated", False):
        return DASHBOARD_PROFILES["client"]
    if getattr(user, "is_superuser", False):
        return DASHBOARD_PROFILES["admin"]

    if role_codes is None or permission_codes is None:
        loaded_roles, loaded_permissions = _active_access(user)
        role_codes = loaded_roles if role_codes is None else role_codes
        permission_codes = loaded_permissions if permission_codes is None else permission_codes

    # Role names choose the most familiar landing only when the matching real
    # capability is still present. Custom roles fall through to permissions.

    if role_codes & ADMIN_ROLE_CODES and permission_codes.intersection(PROFILE_PERMISSION_PRIORITY[0][1]):
        return DASHBOARD_PROFILES["admin"]
    if role_codes & BRANCH_ROLE_CODES and permission_codes.intersection(
        ("branches.manage", "vehicles.view", "vehicles.manage", "inventory.view", "inventory.manage_stock")
    ):
        return DASHBOARD_PROFILES["branch"]
    if role_codes & COMMERCIAL_ROLE_CODES and permission_codes.intersection(("sales.quote", "sales.reserve", "sales.sell")):
        return DASHBOARD_PROFILES["commercial"]
    if role_codes & SELLER_ROLE_CODES and permission_codes.intersection(("sales.quote", "sales.reserve", "sales.sell")):
        return DASHBOARD_PROFILES["seller"]
    if role_codes & INVENTORY_ROLE_CODES and permission_codes.intersection(("inventory.view", "inventory.manage_stock")):
        return DASHBOARD_PROFILES["inventory"]
    if role_codes & BILLING_ROLE_CODES and permission_codes.intersection(
        ("invoices.issue", "invoices.manage", "documents.manage", "sales.sell")
    ):
        return DASHBOARD_PROFILES["billing"]
    if role_codes & SUPPORT_ROLE_CODES and permission_codes.intersection(
        ("customers.view", "customers.manage", "notifications.view", "notifications.send")
    ):
        return DASHBOARD_PROFILES["support"]
    if role_codes & MARKETING_ROLE_CODES and permission_codes.intersection(("vehicles.manage", "vehicles.publish")):
        return DASHBOARD_PROFILES["marketing"]
    if role_codes & AUDITOR_ROLE_CODES and permission_codes.intersection(
        ("reports.view", "audit.view", "documents.view")
    ):
        return DASHBOARD_PROFILES["auditor"]
    if role_codes & CLIENT_ROLE_CODES and not permission_codes.intersection(
        {permission for _, permissions in PROFILE_PERMISSION_PRIORITY for permission in permissions} | {"dashboard.view"}
    ):
        return DASHBOARD_PROFILES["client"]

    for profile_code, required in PROFILE_PERMISSION_PRIORITY:
        if permission_codes.intersection(required):
            return DASHBOARD_PROFILES[profile_code]
    if "dashboard.view" in permission_codes or getattr(user, "can_access_internal_panel", False):
        return DASHBOARD_PROFILES["worker"]
    return DASHBOARD_PROFILES["client"]
