"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de paneles.

EN: This module orchestrates HTTP requests, permissions, and responses for the dashboard domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the dashboard domain.
"""

from __future__ import annotations

import json

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_GET, require_POST
from django.views.generic import TemplateView

from apps.dashboard.selectors import (
    adaptive_dashboard_context,
    public_home_context,
)
from apps.dashboard.services import dashboard_manifest_for_user
from apps.common.assist import assist_response_for_user
from apps.common.universal_search import universal_search_for_user


DASHBOARD_HEADINGS = {
    "admin": "Dashboard administrador",
    "branch": "Dashboard de sucursal",
    "commercial": "Dashboard comercial",
    "seller": "Dashboard vendedor",
    "inventory": "Dashboard de inventario",
    "billing": "Dashboard de facturación",
    "support": "Dashboard de atención",
    "marketing": "Dashboard de marketing",
    "auditor": "Dashboard de auditoría",
    "worker": "Dashboard operativo",
}


def _apply_manifest_context(context, user, preferences=None):
    manifest = dashboard_manifest_for_user(user, preferences)
    context["dashboard_profile"] = manifest.profile
    context["dashboard_heading"] = DASHBOARD_HEADINGS.get(manifest.profile.code, "Mi dashboard")
    context["recommended_url"] = reverse(manifest.profile.url_name)
    context.update(adaptive_dashboard_context(user, manifest))
    return context


class PublicHomeView(TemplateView):
    """Portada pública de concesionaria.

    Esta vista representa la cara comercial de Vinova Pro. No expone paneles,
    usuarios, roles ni información operativa interna.
    """

    template_name = "dashboard/public_home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(public_home_context())
        return ctx


class PublicServicesView(PublicHomeView):
    """Public services entry point; content remains shared with the home page."""


class PublicAboutView(PublicHomeView):
    """Public company entry point; content remains shared with the home page."""


class DashboardRouterView(LoginRequiredMixin, TemplateView):
    """Entrada segura al panel correcto.

    Mantiene /dashboard/ como puerta estable y comprensible. No mezcla todas las
    funciones en una sola pantalla; muestra el perfil recomendado y enlaces solo
    a experiencias permitidas. Esto evita pantallas en blanco o confusión cuando
    un usuario entra manualmente a /dashboard/.
    """

    template_name = "dashboard/adaptive.html"

    def get(self, request, *args, **kwargs):
        if not request.user.can_access_internal_panel:
            return redirect(reverse("accounts:profile"))
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        return _apply_manifest_context(
            ctx, self.request.user, self.request.session.get("vinova_dashboard_preferences")
        )


class InternalDashboardAccessMixin(LoginRequiredMixin):
    dashboard_code: str | None = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.can_access_internal_panel:
            raise PermissionDenied("No tienes acceso al área interna.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["dashboard_code"] = self.dashboard_code
        return _apply_manifest_context(
            ctx, self.request.user, self.request.session.get("vinova_dashboard_preferences")
        )


class StaffDashboardView(InternalDashboardAccessMixin, TemplateView):
    """Dashboard operativo mínimo conservado como compatibilidad interna."""

    dashboard_code = "worker"
    template_name = "dashboard/adaptive.html"


class AdminDashboardView(InternalDashboardAccessMixin, TemplateView):
    dashboard_code = "admin"
    template_name = "dashboard/adaptive.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.is_superuser or request.user.has_role("superadmin") or request.user.has_role("admin_general") or request.user.can_manage_users):
            raise PermissionDenied("Este dashboard es solo para administración general.")
        return super().dispatch(request, *args, **kwargs)

class BranchDashboardView(InternalDashboardAccessMixin, TemplateView):
    dashboard_code = "branch"
    template_name = "dashboard/adaptive.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.has_role("admin_sucursal") or request.user.can_manage_branches):
            raise PermissionDenied("Este dashboard es solo para administración de sucursal.")
        return super().dispatch(request, *args, **kwargs)

class CommercialDashboardView(InternalDashboardAccessMixin, TemplateView):
    dashboard_code = "commercial"
    template_name = "dashboard/adaptive.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.has_role("gerente_comercial") or request.user.can_confirm_sales):
            raise PermissionDenied("Este dashboard es solo para gerencia comercial.")
        return super().dispatch(request, *args, **kwargs)

class SellerDashboardView(InternalDashboardAccessMixin, TemplateView):
    dashboard_code = "seller"
    template_name = "dashboard/adaptive.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.can_access_sales:
            raise PermissionDenied("Este dashboard es solo para equipo comercial.")
        return super().dispatch(request, *args, **kwargs)

class InventoryDashboardView(InternalDashboardAccessMixin, TemplateView):
    dashboard_code = "inventory"
    template_name = "dashboard/adaptive.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.can_view_inventory:
            raise PermissionDenied("Este dashboard es solo para inventario y bodega.")
        return super().dispatch(request, *args, **kwargs)

class BillingDashboardView(InternalDashboardAccessMixin, TemplateView):
    dashboard_code = "billing"
    template_name = "dashboard/adaptive.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.can_issue_invoices or request.user.can_manage_documents or request.user.can_confirm_sales):
            raise PermissionDenied("Este dashboard es solo para facturación/documentación.")
        return super().dispatch(request, *args, **kwargs)

class SupportDashboardView(InternalDashboardAccessMixin, TemplateView):
    dashboard_code = "support"
    template_name = "dashboard/adaptive.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.can_view_customers or request.user.can_view_notifications):
            raise PermissionDenied("Este dashboard es solo para atención al cliente/postventa.")
        return super().dispatch(request, *args, **kwargs)

class MarketingDashboardView(InternalDashboardAccessMixin, TemplateView):
    dashboard_code = "marketing"
    template_name = "dashboard/adaptive.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.can_manage_vehicles or request.user.can_publish_vehicles):
            raise PermissionDenied("Este dashboard es solo para catálogo/marketing.")
        return super().dispatch(request, *args, **kwargs)

class AuditorDashboardView(InternalDashboardAccessMixin, TemplateView):
    dashboard_code = "auditor"
    template_name = "dashboard/adaptive.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.can_view_reports or request.user.can_view_audit or request.user.has_role("auditor")):
            raise PermissionDenied("Este dashboard es solo para auditoría o lectura autorizada.")
        return super().dispatch(request, *args, **kwargs)

class WorkerDashboardView(InternalDashboardAccessMixin, TemplateView):
    dashboard_code = "worker"
    template_name = "dashboard/adaptive.html"


@require_GET
def assist_query(request):
    if not request.user.is_authenticated or not request.user.can_access_internal_panel:
        raise PermissionDenied("No tienes acceso al área interna.")
    return JsonResponse(assist_response_for_user(request.user, request.GET.get("q", "")))


@require_GET
def universal_search(request):
    if not request.user.is_authenticated or not request.user.can_access_internal_panel:
        raise PermissionDenied("No tienes acceso al área interna.")
    return JsonResponse(universal_search_for_user(request.user, request.GET.get("q", "")))


@require_POST
def dashboard_preferences(request):
    """Persist only authorized ordering keys in the current authenticated session."""

    if not request.user.is_authenticated or not request.user.can_access_internal_panel:
        raise PermissionDenied("No tienes acceso al área interna.")
    try:
        payload = json.loads(request.body or "{}")
    except (json.JSONDecodeError, UnicodeDecodeError):
        return JsonResponse({"error": "Preferencias inválidas."}, status=400)
    manifest = dashboard_manifest_for_user(request.user)
    allowed_widgets = {widget.key for widget in manifest.widgets}
    allowed_actions = {action["key"] for action in manifest.actions}

    def sanitize(value, allowed):
        if not isinstance(value, list):
            return []
        return list(dict.fromkeys(key for key in value if isinstance(key, str) and key in allowed))

    preferences = {
        "widget_order": sanitize(payload.get("widget_order"), allowed_widgets),
        "action_order": sanitize(payload.get("action_order"), allowed_actions),
    }
    request.session["vinova_dashboard_preferences"] = preferences
    return JsonResponse(preferences)
