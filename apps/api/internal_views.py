"""ES: Este módulo implementa el componente internal views para el dominio de API e integraciones.

EN: This module implements the internal views component for the api domain.

Contexto existente / Existing context:
Internal views support for the api domain.
"""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import TemplateView

from apps.accounts.views import PermissionCodeRequiredMixin
from apps.api.forms import APIClientForm, WebhookEndpointForm
from apps.api.models import APIClient, IntegrationLog, WebhookDelivery, WebhookEndpoint
from apps.api.selectors import scope_integration_queryset
from apps.api.services import issue_api_client_token, issue_webhook_secret, publish_webhook_event
from apps.audit.services import audit_log


class IntegrationAccessMixin(PermissionCodeRequiredMixin):
    permission_code = "integrations.view"


class IntegrationDashboardView(IntegrationAccessMixin, TemplateView):
    template_name = "api/internal/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        clients = scope_integration_queryset(
            APIClient.objects.select_related("service_user", "branch").prefetch_related("scopes"),
            self.request.user,
            "branch_id",
        )
        endpoints = scope_integration_queryset(
            WebhookEndpoint.objects.select_related("branch", "created_by"),
            self.request.user,
            "branch_id",
        )
        deliveries = scope_integration_queryset(
            WebhookDelivery.objects.select_related("endpoint", "event", "event__branch"),
            self.request.user,
            "event__branch_id",
        )
        logs = scope_integration_queryset(
            IntegrationLog.objects.select_related("client", "branch"),
            self.request.user,
            "branch_id",
        )
        ctx.update({
            "client_count": clients.filter(is_active=True).count(),
            "webhook_count": endpoints.filter(is_active=True).count(),
            "failed_delivery_count": deliveries.filter(status=WebhookDelivery.Status.FAILED).count(),
            "recent_clients": clients[:8],
            "recent_deliveries": deliveries[:8],
            "recent_logs": logs[:10],
        })
        return ctx


class APIClientCreateView(IntegrationAccessMixin, View):
    template_name = "api/internal/api_client_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.has_perm_code("integrations.manage"):
            raise PermissionDenied("No tienes permiso para administrar integraciones.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, self.template_name, {"form": APIClientForm(user=request.user)})

    def post(self, request):
        form = APIClientForm(request.POST, user=request.user)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})
        client = form.save(commit=False)
        client.created_by = request.user
        client.full_clean()
        client.save()
        form.save_m2m()
        token = issue_api_client_token(client, actor=request.user)
        audit_log(user=request.user, action="integrations.api_client.create", target=client, after={"scopes": sorted(client.scope_codes())})
        return render(request, "api/internal/secret_once.html", {
            "title": "Cliente API creado",
            "label": "Token Bearer",
            "secret": token,
            "back_url": "api_internal:dashboard",
        })


class APIClientRotateView(IntegrationAccessMixin, View):
    def post(self, request, public_id):
        if not request.user.has_perm_code("integrations.manage"):
            raise PermissionDenied("No tienes permiso para rotar credenciales.")
        client = get_object_or_404(scope_integration_queryset(APIClient.objects.all(), request.user, "branch_id"), public_id=public_id)
        token = issue_api_client_token(client, actor=request.user)
        audit_log(user=request.user, action="integrations.api_client.rotate", target=client)
        return render(request, "api/internal/secret_once.html", {
            "title": "Credencial rotada",
            "label": "Nuevo token Bearer",
            "secret": token,
            "back_url": "api_internal:dashboard",
        })


class WebhookCreateView(IntegrationAccessMixin, View):
    template_name = "api/internal/webhook_form.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.has_perm_code("integrations.manage"):
            raise PermissionDenied("No tienes permiso para administrar webhooks.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        return render(request, self.template_name, {"form": WebhookEndpointForm(user=request.user)})

    def post(self, request):
        form = WebhookEndpointForm(request.POST, user=request.user)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})
        endpoint = form.save(commit=False)
        endpoint.created_by = request.user
        endpoint.save()
        secret = issue_webhook_secret(endpoint, actor=request.user)
        audit_log(user=request.user, action="integrations.webhook.create", target=endpoint, after={"events": endpoint.event_types})
        return render(request, "api/internal/secret_once.html", {
            "title": "Webhook creado",
            "label": "Secreto de firma",
            "secret": secret,
            "back_url": "api_internal:dashboard",
        })


class WebhookTestView(IntegrationAccessMixin, View):
    def post(self, request, public_id):
        if not request.user.has_perm_code("integrations.manage"):
            raise PermissionDenied("No tienes permiso para probar webhooks.")
        endpoint = get_object_or_404(scope_integration_queryset(WebhookEndpoint.objects.all(), request.user, "branch_id"), public_id=public_id)
        event = publish_webhook_event(
            event_type="integration.test",
            aggregate_type="webhook_endpoint",
            aggregate_id=endpoint.public_id,
            branch=endpoint.branch,
            payload={"message": "Prueba operativa de Vinova Pro", "endpoint_id": str(endpoint.public_id)},
        )
        if event:
            messages.success(request, f"Evento {event.event_id} enviado a la cola.")
        else:
            messages.warning(request, "El endpoint debe suscribirse a integration.test o *.")
        return redirect("api_internal:dashboard")
