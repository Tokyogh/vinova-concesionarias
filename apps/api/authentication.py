"""ES: Este módulo aplica autenticación y validación de credenciales para el dominio de API e integraciones.

EN: This module enforces authentication and credential validation for the api domain.

Contexto existente / Existing context:
Authentication and credential enforcement for the api domain.
"""

from __future__ import annotations

import ipaddress
import uuid
from urllib.parse import unquote

from django.utils import timezone
from rest_framework.authentication import BaseAuthentication, get_authorization_header
from rest_framework.exceptions import AuthenticationFailed, PermissionDenied

from apps.api.models import APIClient

READ_METHODS = {"GET", "HEAD", "OPTIONS"}
RESOURCE_SCOPES = {
    "users": "users",
    "roles": "users",
    "audit-logs": "audit",
    "security-alerts": "audit",
    "backup-policies": "continuity",
    "backups": "continuity",
    "restore-drills": "continuity",
    "privacy-consents": "privacy",
    "data-subject-requests": "privacy",
    "data-exports": "privacy",
    "retention-policies": "privacy",
    "security-policies": "security",
    "security-sessions": "security",
    "leads": "leads",
    "lead-activities": "leads",
    "test-drives": "leads",
    "vehicle-interactions": "analytics",
    "commercial-analytics": "analytics",
    "reports": "reports",
    "companies": "companies",
    "branches": "branches",
    "vehicles": "vehicles",
    "customers": "customers",
    "customer-notes": "customers",
    "customer-interests": "customers",
    "inventory-categories": "inventory",
    "inventory-items": "inventory",
    "inventory-stock": "inventory",
    "inventory-movements": "inventory",
    "sales": "sales",
    "sale-lines": "sales",
    "sale-payments": "sales",
    "sale-status-history": "sales",
    "documents": "documents",
    "document-categories": "documents",
    "reusable-assets": "documents",
    "notification-messages": "notifications",
    "notification-recipients": "notifications",
    "notification-templates": "notifications",
    "invoices": "invoices",
    "invoice-lines": "invoices",
    "invoice-payments": "invoices",
    "invoice-sequences": "invoices",
    "invoice-status-history": "invoices",
    "company-public-settings": "enterprise",
    "approval-policies": "enterprise",
    "sri-configurations": "sri",
    "sri-establishments": "sri",
    "sri-sequences": "sri",
    "imports": "imports",
    "import-rows": "imports",
    "api-clients": "integrations",
    "api-scopes": "integrations",
    "webhook-endpoints": "integrations",
    "webhook-events": "integrations",
    "webhook-deliveries": "integrations",
    "integration-logs": "integrations",
}

# A branch-bound credential must not read installation-wide configuration or
# continuity/security material that cannot be filtered safely by branch.
GLOBAL_ONLY_RESOURCES = {
    "roles",
    "companies",
    "backup-policies",
    "backups",
    "restore-drills",
    "retention-policies",
    "security-policies",
    "company-public-settings",
    "approval-policies",
    "sri-configurations",
    "sri-establishments",
    "sri-sequences",
    "api-clients",
    "api-scopes",
}

# The scope is necessary but never sufficient. The service user must retain
# the corresponding Vinova business permission, so revoking a role also
# revokes API capability without rotating every token.
SCOPE_PERMISSION_MAP = {
    "users:read": ("accounts.manage_users",),
    "users:write": ("accounts.manage_users",),
    "companies:read": ("companies.manage",),
    "companies:write": ("companies.manage",),
    "branches:read": ("branches.manage",),
    "branches:write": ("branches.manage",),
    "vehicles:read": ("vehicles.view", "vehicles.manage"),
    "vehicles:write": ("vehicles.manage",),
    "customers:read": ("customers.view", "customers.manage"),
    "customers:write": ("customers.manage",),
    "inventory:read": ("inventory.view", "inventory.manage_stock"),
    "inventory:write": ("inventory.manage_stock",),
    "sales:read": ("sales.quote", "sales.reserve", "sales.sell"),
    "sales:write": ("sales.quote", "sales.reserve", "sales.sell"),
    "invoices:read": ("invoices.view", "invoices.issue", "invoices.manage"),
    "invoices:write": ("invoices.issue", "invoices.manage"),
    "documents:read": ("documents.view", "documents.manage", "documents.download_private"),
    "documents:write": ("documents.manage",),
    "notifications:read": ("notifications.view", "notifications.send"),
    "notifications:write": ("notifications.send",),
    "reports:read": ("reports.view",),
    "imports:read": ("imports.manage",),
    "imports:write": ("imports.manage",),
    "enterprise:read": ("enterprise.manage",),
    "enterprise:write": ("enterprise.manage",),
    "sri:read": ("sri.manage",),
    "sri:write": ("sri.manage",),
    "audit:read": ("audit.view",),
    "security:read": ("security.view", "security.manage"),
    "security:write": ("security.manage",),
    "continuity:read": ("continuity.view", "continuity.manage"),
    "continuity:write": ("continuity.manage",),
    "privacy:read": ("privacy.view", "privacy.manage", "privacy.export"),
    "privacy:write": ("privacy.manage",),
    "leads:read": ("leads.view", "leads.manage"),
    "leads:write": ("leads.manage",),
    "analytics:read": ("analytics.view", "analytics.export"),
    "integrations:read": ("integrations.view", "integrations.manage"),
    "integrations:manage": ("integrations.manage",),
    "bi:read": ("analytics.export", "data.export"),
    "accounting:export": ("data.export", "invoices.view"),
}


def _client_ip(request) -> str:
    # AuditRequestMiddleware resolves the trusted proxy chain before DRF
    # authentication. Fall back to REMOTE_ADDR when no audited value exists.
    value = getattr(request, "audit_ip", "") or request.META.get("REMOTE_ADDR", "")
    try:
        return str(ipaddress.ip_address(value))
    except ValueError:
        return ""


def _path_parts(request) -> list[str]:
    parts = unquote(request.path).strip("/").split("/")
    if parts[:2] == ["api", "v1"]:
        return parts[2:]
    if parts[:1] == ["api"]:
        return parts[1:]
    return parts


def required_scope(request) -> str:
    parts = _path_parts(request)
    resource = parts[0] if parts else ""
    if resource == "bi":
        return "bi:read"
    if resource == "integrations":
        if len(parts) > 1 and parts[1] == "accounting":
            return "accounting:export"
        if len(parts) > 1 and parts[1] == "leads":
            return "leads:write"
        return "integrations:read" if request.method in READ_METHODS else "integrations:manage"
    namespace = RESOURCE_SCOPES.get(resource, "api")
    action = "read" if request.method in READ_METHODS else "write"
    return f"{namespace}:{action}"


def _enforce_branch_request(client: APIClient, request) -> None:
    if not client.branch_id:
        return
    parts = _path_parts(request)
    resource = parts[0] if parts else ""
    if resource in GLOBAL_ONLY_RESOURCES:
        raise PermissionDenied(
            "Este cliente API está limitado a una sucursal y no puede acceder a este recurso global."
        )
    for key in ("branch", "assigned_branch"):
        query_value = request.query_params.get(key)
        if query_value and str(query_value) != str(client.branch_id):
            raise PermissionDenied("La sucursal solicitada está fuera del alcance del cliente API.")
    if request.method not in READ_METHODS and request.content_type and "json" in request.content_type:
        try:
            data = request.data
        except Exception:  # pragma: no cover - DRF reports malformed bodies separately
            data = {}
        for key in ("branch", "assigned_branch"):
            value = data.get(key) if hasattr(data, "get") else None
            if value not in (None, "", client.branch_id, str(client.branch_id)):
                raise PermissionDenied("La sucursal enviada está fuera del alcance del cliente API.")


def _enforce_service_user_permission(client: APIClient, scope: str) -> None:
    permissions = SCOPE_PERMISSION_MAP.get(scope, ())
    if not permissions or client.service_user.is_superuser:
        return
    if not any(client.service_user.has_perm_code(code, branch=client.branch) for code in permissions):
        raise PermissionDenied(
            "El usuario de servicio no posee el permiso empresarial requerido para este recurso."
        )


class APIClientAuthentication(BaseAuthentication):
    """ES: Agrupa el componente «a p i client authentication» del dominio de API e integraciones y sus reglas relacionadas. Además, aplica autorización en backend.

    EN: Groups the «a p i client authentication» component and its related rules in the api domain. It also enforces server-side authorization.
    """

    keyword = "Bearer"

    def authenticate(self, request):
        """ES: Ejecuta la operación «authenticate» dentro del dominio de API e integraciones. Además, aplica autorización en backend.

        EN: Executes the «authenticate» operation within the api domain. It also enforces server-side authorization.
        """

        header = get_authorization_header(request).decode("utf-8")
        if not header:
            return None
        pieces = header.split()
        if len(pieces) != 2 or pieces[0].lower() != self.keyword.lower():
            return None
        token = pieces[1]
        if not token.startswith("vnp_") or "." not in token:
            raise AuthenticationFailed("Credencial API inválida.")
        public_part, raw_secret = token[4:].split(".", 1)
        try:
            public_id = str(uuid.UUID(public_part)) if len(public_part) == 36 else str(uuid.UUID(hex=public_part))
            client = (
                APIClient.objects.select_related("service_user", "branch")
                .prefetch_related("scopes")
                .get(public_id=public_id)
            )
        except (ValueError, APIClient.DoesNotExist) as exc:
            raise AuthenticationFailed("Credencial API inválida.") from exc

        ip = _client_ip(request)
        if not client.is_active or client.is_expired or not client.service_user.is_active:
            raise AuthenticationFailed("Credencial API inactiva o vencida.")
        if not client.verify_secret(raw_secret):
            raise AuthenticationFailed("Credencial API inválida.")
        if not ip or not client.allows_ip(ip):
            raise AuthenticationFailed("Origen no autorizado para este cliente API.")

        scope = required_scope(request)
        if not client.has_scope(scope):
            raise PermissionDenied(f"El cliente API no posee el alcance requerido: {scope}.")
        _enforce_service_user_permission(client, scope)
        _enforce_branch_request(client, request)

        request.api_client = client
        request._request._vinova_api_client = client
        APIClient.objects.filter(pk=client.pk).update(last_used_at=timezone.now(), last_used_ip=ip)
        return client.service_user, client

    def authenticate_header(self, request):
        return self.keyword
