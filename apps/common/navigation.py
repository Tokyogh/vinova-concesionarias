"""ES: Este módulo implementa el componente navigation para el dominio de infraestructura compartida.

EN: This module implements the navigation component for the common domain.

Contexto existente / Existing context:
Registro de navegación interna de VINOVA PRO (VINOVA NEXT N02).

Una única fuente para:

- secciones del sidebar staff (rellenos con el fallback invariante de la marca);
- breadcrumbs de la página actual;
- validación de favoritos/recientes (localStorage por usuario);
- paleta de comandos Ctrl+K.

Todas las operaciones son puramente en memoria: no ejecutan consultas SQL.
La autorización se deriva de los permisos reales de ``request.user``, de modo
que un destino nunca aparece si el usuario no puede accederlo.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from django.urls import reverse


@dataclass(frozen=True)
class NavDestination:
    key: str
    title: str
    area: str
    url_name: str
    allow: str | None = None
    module: str | None = None
    keywords: tuple = ()
    path_prefix: str | None = None
    exact: bool = False
    excluded_prefix: str | None = None

    def _url(self) -> str:
        return reverse(self.url_name)

    def matches(self, path: str) -> bool:
        prefix = self.path_prefix
        if prefix is None:
            return False
        if self.exact:
            return path == prefix
        if not path.startswith(prefix):
            return False
        if self.excluded_prefix and path.startswith(self.excluded_prefix):
            return False
        return True


@dataclass(frozen=True)
class NavGroup:
    key: str
    title: str
    items: tuple = field(default_factory=tuple)


# Áreas en el orden canónico de presentación. FAVORITOS y RECIENTES no se
# definen aquí: son secciones dinámicas renderizadas en el cliente a partir de
# los destinos autorizados del usuario.
NAV_GROUPS = (
    NavGroup(
        key="panel",
        title="Panel",
        items=(
            NavDestination(
                key="dashboard",
                title="Mi dashboard",
                area="Panel",
                url_name="dashboard:staff_home",
                path_prefix="/dashboard/",
                exact=True,
                keywords=("inicio", "resumen", "home", "panel"),
            ),
        ),
    ),
    NavGroup(
        key="operacion",
        title="Operación",
        items=(
            NavDestination(
                key="vehicles",
                title="Vehículos",
                area="Operación",
                url_name="vehicles_internal:list",
                allow="can_view_internal_vehicles",
                path_prefix="/dashboard/vehicles",
                keywords=("autos", "stock", "unidades", "inventario", "placa", "vin"),
            ),
            NavDestination(
                key="customers",
                title="Clientes",
                area="Operación",
                url_name="customers_internal:list",
                allow="can_view_customers",
                path_prefix="/dashboard/customers",
                keywords=("clientes", "personas", "cedula", "ruc"),
            ),
            NavDestination(
                key="leads",
                title="CRM y leads",
                area="Operación",
                url_name="leads_internal:list",
                allow="can_view_leads",
                path_prefix="/dashboard/leads",
                keywords=("crm", "prospectos", "oportunidades", "pipeline"),
            ),
            NavDestination(
                key="sales",
                title="Ventas",
                area="Operación",
                url_name="sales_internal:list",
                allow="can_access_sales",
                path_prefix="/dashboard/sales",
                keywords=("ventas", "comercial", "negociaciones"),
            ),
            NavDestination(
                key="inventory",
                title="Inventario",
                area="Operación",
                url_name="inventory_internal:list",
                allow="can_view_inventory",
                path_prefix="/dashboard/inventory",
                keywords=("inventario", "items", "repuestos", "accesorios", "stock"),
            ),
            NavDestination(
                key="post_sales",
                title="Postventa",
                area="Operación",
                url_name="post_sales:list",
                module="post_sales",
                path_prefix="/dashboard/post-sales",
                keywords=("postventa", "talleres", "servicios", "mantenimiento", "ordenes"),
            ),
        ),
    ),
    NavGroup(
        key="seguimiento",
        title="Seguimiento",
        items=(
            NavDestination(
                key="documents",
                title="Documentos",
                area="Seguimiento",
                url_name="documents_internal:list",
                allow="can_view_documents",
                path_prefix="/dashboard/documents",
                keywords=("documentos", "archivo", "registro"),
            ),
            NavDestination(
                key="invoices",
                title="Facturación",
                area="Seguimiento",
                url_name="invoices_internal:list",
                allow="can_view_invoices",
                path_prefix="/dashboard/invoices",
                keywords=("facturas", "facturacion", "pagos", "documentos tributarios"),
            ),
            NavDestination(
                key="notifications",
                title="Notificaciones",
                area="Seguimiento",
                url_name="notifications_internal:inbox",
                allow="can_view_notifications",
                path_prefix="/dashboard/notifications",
                keywords=("notificaciones", "bandeja", "avisos", "alertas"),
            ),
        ),
    ),
    NavGroup(
        key="datos",
        title="Datos",
        items=(
            NavDestination(
                key="reports",
                title="Reportes",
                area="Datos",
                url_name="reports_internal:home",
                allow="can_view_reports",
                path_prefix="/dashboard/reports",
                keywords=("reportes", "informes", "indicadores"),
            ),
            NavDestination(
                key="analytics",
                title="Analítica comercial",
                area="Datos",
                url_name="analytics_internal:home",
                allow="can_view_analytics",
                path_prefix="/dashboard/analytics",
                keywords=("analitica", "graficos", "metricas", "comercial"),
            ),
            NavDestination(
                key="imports",
                title="Importaciones",
                area="Datos",
                url_name="imports_internal:home",
                allow="can_manage_imports",
                path_prefix="/dashboard/imports",
                keywords=("importaciones", "carga", "masiva", "excel", "csv"),
            ),
            NavDestination(
                key="integrations",
                title="Integraciones y BI",
                area="Datos",
                url_name="api_internal:dashboard",
                allow="can_view_integrations",
                path_prefix="/dashboard/integrations",
                keywords=("integraciones", "api", "bi", "webhooks", "conectores"),
            ),
        ),
    ),
    NavGroup(
        key="administracion",
        title="Administración",
        items=(
            NavDestination(
                key="enterprise",
                title="Centro empresarial",
                area="Administración",
                url_name="enterprise:home",
                allow="can_manage_enterprise_settings",
                path_prefix="/dashboard/company",
                keywords=("empresa", "configuracion", "organizacion", "centro"),
            ),
            NavDestination(
                key="companies",
                title="Empresas",
                area="Administración",
                url_name="companies:list",
                allow="can_manage_companies",
                path_prefix="/companies",
                keywords=("empresas", "companias", "organizaciones"),
            ),
            NavDestination(
                key="branches",
                title="Sucursales",
                area="Administración",
                url_name="branches:list",
                allow="can_manage_branches",
                path_prefix="/branches",
                keywords=("sucursales", "sedes", "puntos"),
            ),
            NavDestination(
                key="users",
                title="Usuarios y roles",
                area="Administración",
                url_name="accounts:user_list",
                allow="can_manage_users",
                path_prefix="/accounts/users",
                keywords=("usuarios", "roles", "cuentas", "permisos", "acceso"),
            ),
        ),
    ),
    NavGroup(
        key="control",
        title="Control y cumplimiento",
        items=(
            NavDestination(
                key="audit",
                title="Auditoría avanzada",
                area="Control y cumplimiento",
                url_name="audit_internal:list",
                allow="can_view_audit",
                path_prefix="/dashboard/audit",
                excluded_prefix="/dashboard/audit/alerts",
                keywords=("auditoria", "registro", "actividad", "logs"),
            ),
            NavDestination(
                key="audit_alerts",
                title="Alertas de seguridad",
                area="Control y cumplimiento",
                url_name="audit_internal:alerts",
                allow="can_view_audit",
                path_prefix="/dashboard/audit/alerts",
                keywords=("alertas", "seguridad", "ataques", "eventos"),
            ),
            NavDestination(
                key="continuity",
                title="Backups y recuperación",
                area="Control y cumplimiento",
                url_name="continuity:dashboard",
                allow="can_view_continuity",
                path_prefix="/dashboard/continuity",
                excluded_prefix="/dashboard/continuity/updates",
                keywords=("backups", "respaldo", "recuperacion", "restore"),
            ),
            NavDestination(
                key="update_center",
                title="Actualizaciones",
                area="Control y cumplimiento",
                url_name="continuity:update_center",
                allow="can_view_continuity",
                path_prefix="/dashboard/continuity/updates",
                keywords=("actualizaciones", "version", "release", "preflight", "sistema"),
            ),
            NavDestination(
                key="privacy",
                title="Protección de datos",
                area="Control y cumplimiento",
                url_name="privacy:dashboard",
                allow="can_view_privacy",
                path_prefix="/dashboard/privacy",
                keywords=("privacidad", "datos", "rgpd", "lopd", "consentimiento"),
            ),
            NavDestination(
                key="security",
                title="Seguridad y hardening",
                area="Control y cumplimiento",
                url_name="security_center:dashboard",
                allow="can_view_security",
                path_prefix="/dashboard/security",
                keywords=("seguridad", "hardening", "firewall", "2fa", "mfa"),
            ),
            NavDestination(
                key="quality",
                title="QA Bot y release",
                area="Control y cumplimiento",
                url_name="quality:run_list",
                allow="can_view_quality",
                path_prefix="/dashboard/quality",
                keywords=("qa", "pruebas", "release", "control de calidad"),
            ),
        ),
    ),
    NavGroup(
        key="soporte",
        title="Soporte",
        items=(
            NavDestination(
                key="help",
                title="Ayuda y capacitación",
                area="Soporte",
                url_name="help_center:home",
                allow="can_view_help",
                path_prefix="/dashboard/help",
                keywords=("ayuda", "soporte", "capacitacion", "checklists", "guias"),
            ),
        ),
    ),
)

# Índice llano de todos los destinos declarados.
ALL_DESTINATIONS: dict[str, NavDestination] = {
    item.key: item for group in NAV_GROUPS for item in group.items
}


def is_destination_allowed(destination: NavDestination, user, modules) -> bool:
    """Valida un destino frente a los permisos y módulos reales del usuario."""
    if destination.module and not modules.get(destination.module, False):
        return False
    if destination.allow:
        return bool(getattr(user, destination.allow, False))
    return True


def authorized_destinations(user, modules=None) -> list[NavDestination]:
    """Destinos a los que el usuario realmente puede acceder (orden canónico)."""
    modules = modules or {}
    return [
        destination
        for group in NAV_GROUPS
        for destination in group.items
        if is_destination_allowed(destination, user, modules)
    ]


def authorized_groups(user, modules=None, path: str | None = None) -> list[dict]:
    """Grupos de navegación filtrados por autorización y módulos.

    Devuelve estructuras planas (dict) listas para template/JSON, con la url
    resuelta y el estado de navegación actual cuando ``path`` se proporciona.
    """
    modules = modules or {}
    groups = []
    for group in NAV_GROUPS:
        items = []
        for destination in group.items:
            if not is_destination_allowed(destination, user, modules):
                continue
            items.append(
                {
                    "key": destination.key,
                    "title": destination.title,
                    "area": destination.area,
                    "url": destination._url(),
                    "active": destination.matches(path) if path else False,
                    "keywords": list(destination.keywords),
                }
            )
        if items:
            groups.append({"key": group.key, "title": group.title, "items": items})
    return groups


def current_destination(path: str, destinations) -> NavDestination | None:
    """Detecta el destino correspondiente a un ``request.path`` dado."""
    for destination in destinations:
        if destination.matches(path):
            return destination
    return None


def destination_state(destination, path: str) -> dict:
    """Serialización de un destino con su estado de navegación actual."""
    return {
        "key": destination.key,
        "title": destination.title,
        "area": destination.area,
        "url": destination._url(),
        "active": destination.matches(path),
    }


STAFF_SHELL_PREFIXES = (
    "/dashboard/",
    "/accounts/",
    "/companies",
    "/branches",
)


def is_staff_shell_path(path: str) -> bool:
    """Rutas que renderizan el shell staff (sidebar + topbar)."""
    return path.startswith(STAFF_SHELL_PREFIXES)


def navigation_modules_for_user(user) -> dict[str, bool]:
    """Estado de módulos que participan en navegación, resuelto una sola vez."""
    from apps.common.modules import is_module_enabled

    return {
        "post_sales": bool(
            is_module_enabled("post_sales")
            and (
                user.has_perm_code("post_sales.view")
                or user.has_perm_code("post_sales.manage")
            )
        ),
    }


def navigation_context(request) -> dict:
    """Contexto de navegación staff para el shell (sin consultas SQL).

    Devuelve los grupos autorizados, el destino actual, breadcrumbs y el
    dataset de destinos autorizados para favoritos/recientes y Ctrl+K.

    Solo computa dentro del shell staff: evita consultas extra en páginas
    públicas o de autenticación.
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    if not is_staff_shell_path(request.path):
        return {}

    modules = navigation_modules_for_user(user)
    destinations = authorized_destinations(user, modules)
    groups = authorized_groups(user, modules, path=request.path)

    current = current_destination(request.path, destinations)
    current_key = current.key if current else None

    destinations_json = [
        {
            "key": destination.key,
            "title": destination.title,
            "area": destination.area,
            "url": destination._url(),
            "keywords": list(destination.keywords),
        }
        for destination in destinations
    ]

    crumbs = [{"title": "Inicio", "url": reverse("dashboard:staff_home")}]
    if current and current.key != "dashboard":
        crumbs.append({"title": current.area, "url": None})
        crumbs.append({"title": current.title, "url": current._url()})

    return {
        "staff_nav_groups": groups,
        "staff_nav_current_key": current_key,
        "staff_nav_crumbs": crumbs if len(crumbs) > 1 else [],
        "staff_nav_json": {
            "userId": getattr(user, "pk", None),
            "destinations": destinations_json,
            "groups": groups,
            "currentKey": current_key,
        },
        "staff_nav_post_sales_enabled": modules["post_sales"],
    }
