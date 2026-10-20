"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de API e integraciones.

EN: This module orchestrates HTTP requests, permissions, and responses for the api domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the api domain.
"""

from __future__ import annotations

import csv
import io

from django.conf import settings
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from drf_spectacular.utils import OpenApiParameter, OpenApiTypes, extend_schema
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.datasets import DATASET_VERSION, accounting_rows, dataset_rows
from apps.api.models import APIClient, APIScope, IntegrationLog, WebhookDelivery, WebhookEndpoint, WebhookEvent
from apps.api.permissions import CanManageIntegrations, CanViewIntegrations, SessionIntegrationAdminOnly
from apps.api.serializers import (
    AccountingExportResponseSerializer,
    APIClientIssuedSerializer,
    APIClientSerializer,
    APIClientTokenResponseSerializer,
    APIScopeSerializer,
    BIDatasetCatalogResponseSerializer,
    BIDatasetResponseSerializer,
    ExternalLeadResponseSerializer,
    ExternalLeadSerializer,
    IntegrationLogSerializer,
    QueuedTaskResponseSerializer,
    StatusResponseSerializer,
    WebhookDeliverySerializer,
    WebhookEndpointIssuedSerializer,
    WebhookEndpointSerializer,
    WebhookEventSerializer,
    WebhookSecretResponseSerializer,
    WebhookTestResponseSerializer,
)
from apps.api.selectors import scope_integration_queryset
from apps.api.services import (
    begin_idempotency,
    complete_idempotency,
    fail_idempotency,
    issue_api_client_token,
    issue_webhook_secret,
    log_integration,
    publish_webhook_event,
)
from apps.audit.services import audit_log


class APIMetadataAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: OpenApiTypes.OBJECT})
    def get(self, request):
        return Response({
            "name": "Vinova Pro API",
            "api_version": "v1",
            "product_version": settings.VINOVA_PRODUCT_VERSION,
            "authenticated_as": "api_client" if getattr(request, "api_client", None) else "session",
            "client": str(getattr(getattr(request, "api_client", None), "public_id", "")),
            "server_time": timezone.now(),
        })


class APIScopeViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = APIScope.objects.filter(is_active=True)
    serializer_class = APIScopeSerializer
    permission_classes = [CanViewIntegrations]
    search_fields = ["code", "name", "description"]


class APIClientViewSet(viewsets.ModelViewSet):
    queryset = APIClient.objects.select_related("service_user", "branch").prefetch_related("scopes")

    def get_queryset(self):
        return scope_integration_queryset(super().get_queryset(), self.request.user, "branch_id")
    serializer_class = APIClientSerializer
    permission_classes = [SessionIntegrationAdminOnly]
    lookup_field = "public_id"
    filterset_fields = ["is_active", "branch", "service_user"]
    search_fields = ["name", "description", "service_user__email"]
    ordering_fields = ["name", "created_at", "last_used_at", "expires_at"]

    def perform_create(self, serializer):
        self.created_client = serializer.save(created_by=self.request.user)

    @extend_schema(responses={201: APIClientIssuedSerializer})
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        token = issue_api_client_token(self.created_client, actor=request.user)
        response.data["token"] = token
        response.data["token_notice"] = "Guarda este token ahora; no volverá a mostrarse."
        audit_log(user=request.user, action="integrations.api_client.create", target=self.created_client, after={"scopes": sorted(self.created_client.scope_codes())})
        return response

    @extend_schema(responses={200: APIClientTokenResponseSerializer})
    @action(detail=True, methods=["post"], url_path="rotate-secret")
    def rotate_secret(self, request, public_id=None):
        client = self.get_object()
        token = issue_api_client_token(client, actor=request.user)
        audit_log(user=request.user, action="integrations.api_client.rotate", target=client)
        return Response({"public_id": client.public_id, "token": token, "token_notice": "Guarda este token ahora; no volverá a mostrarse."})

    @extend_schema(responses={200: StatusResponseSerializer})
    @action(detail=True, methods=["post"])
    def revoke(self, request, public_id=None):
        client = self.get_object()
        client.is_active = False
        client.save(update_fields=["is_active", "updated_at"])
        audit_log(user=request.user, action="integrations.api_client.revoke", target=client)
        return Response({"status": "revoked"})


class WebhookEndpointViewSet(viewsets.ModelViewSet):
    queryset = WebhookEndpoint.objects.select_related("branch", "created_by")

    def get_queryset(self):
        return scope_integration_queryset(super().get_queryset(), self.request.user, "branch_id")
    serializer_class = WebhookEndpointSerializer
    permission_classes = [SessionIntegrationAdminOnly]
    lookup_field = "public_id"
    filterset_fields = ["is_active", "branch"]
    search_fields = ["name", "url"]

    def perform_create(self, serializer):
        self.created_endpoint = serializer.save(created_by=self.request.user)

    @extend_schema(responses={201: WebhookEndpointIssuedSerializer})
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        secret = issue_webhook_secret(self.created_endpoint, actor=request.user)
        response.data["signing_secret"] = secret
        response.data["secret_notice"] = "Guarda este secreto ahora; se utiliza para verificar X-Vinova-Signature."
        audit_log(user=request.user, action="integrations.webhook.create", target=self.created_endpoint, after={"events": self.created_endpoint.event_types})
        return response

    @extend_schema(responses={200: WebhookSecretResponseSerializer})
    @action(detail=True, methods=["post"], url_path="rotate-secret")
    def rotate_secret(self, request, public_id=None):
        endpoint = self.get_object()
        secret = issue_webhook_secret(endpoint, actor=request.user)
        audit_log(user=request.user, action="integrations.webhook.rotate", target=endpoint)
        return Response({"public_id": endpoint.public_id, "signing_secret": secret, "secret_notice": "Guarda este secreto ahora."})

    @extend_schema(responses={202: WebhookTestResponseSerializer})
    @action(detail=True, methods=["post"])
    def test(self, request, public_id=None):
        endpoint = self.get_object()
        event = publish_webhook_event(
            event_type="integration.test",
            aggregate_type="webhook_endpoint",
            aggregate_id=endpoint.public_id,
            branch=endpoint.branch,
            payload={"message": "Prueba de webhook de Vinova Pro", "endpoint_id": str(endpoint.public_id)},
        )
        if event is None:
            return Response({"detail": "El endpoint no está suscrito a integration.test ni a '*'."}, status=400)
        return Response({"event_id": event.event_id, "status": "queued"}, status=202)


class WebhookEventViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WebhookEvent.objects.select_related("branch")

    def get_queryset(self):
        return scope_integration_queryset(super().get_queryset(), self.request.user, "branch_id")
    serializer_class = WebhookEventSerializer
    permission_classes = [CanViewIntegrations]
    lookup_field = "event_id"
    filterset_fields = ["event_type", "branch", "aggregate_type"]
    search_fields = ["aggregate_id", "event_type"]
    ordering_fields = ["occurred_at", "created_at"]


class WebhookDeliveryViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = WebhookDelivery.objects.select_related("endpoint", "event", "event__branch")

    def get_queryset(self):
        return scope_integration_queryset(super().get_queryset(), self.request.user, "event__branch_id")
    serializer_class = WebhookDeliverySerializer
    permission_classes = [CanViewIntegrations]
    lookup_field = "public_id"
    filterset_fields = ["status", "endpoint", "event"]
    ordering_fields = ["created_at", "attempts", "delivered_at"]

    @extend_schema(responses={202: QueuedTaskResponseSerializer})
    @action(detail=True, methods=["post"], permission_classes=[CanManageIntegrations])
    def retry(self, request, public_id=None):
        delivery = self.get_object()
        from apps.api.tasks import deliver_webhook_task

        delivery.status = WebhookDelivery.Status.PENDING
        delivery.error_message = ""
        delivery.save(update_fields=["status", "error_message", "updated_at"])
        result = deliver_webhook_task.apply_async(args=[delivery.pk])
        delivery.celery_task_id = result.id
        delivery.save(update_fields=["celery_task_id", "updated_at"])
        return Response({"status": "queued", "task_id": result.id}, status=202)


class IntegrationLogViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = IntegrationLog.objects.select_related("client", "user", "branch")

    def get_queryset(self):
        return scope_integration_queryset(super().get_queryset(), self.request.user, "branch_id")
    serializer_class = IntegrationLogSerializer
    permission_classes = [CanViewIntegrations]
    lookup_field = "public_id"
    filterset_fields = ["direction", "category", "action", "status", "client", "branch"]
    search_fields = ["action", "endpoint", "error_code", "error_message"]
    ordering_fields = ["created_at", "duration_ms", "http_status"]


class ExternalLeadIngestAPIView(APIView):
    """ES: Agrupa el componente «external lead ingest a p i view» del dominio de API e integraciones y sus reglas relacionadas. Además, conserva atomicidad y bloqueos explícitos, aplica autorización en backend, registra efectos auditables, rechaza estados o entradas inválidas.

    EN: Groups the «external lead ingest a p i view» component and its related rules in the api domain. It also preserves atomicity and explicit locking, enforces server-side authorization, records auditable effects, rejects invalid input or state.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="vinova_external_lead_ingest",
        request=ExternalLeadSerializer,
        parameters=[
            OpenApiParameter(
                "Idempotency-Key",
                OpenApiTypes.STR,
                OpenApiParameter.HEADER,
                required=True,
                description="Clave única por cliente para evitar leads duplicados.",
            )
        ],
        responses={201: ExternalLeadResponseSerializer},
    )
    def post(self, request):
        """ES: Procesa solicitudes POST de ExternalLeadIngestAPIView aplicando el flujo del dominio de API e integraciones. Además, conserva atomicidad y bloqueos explícitos, aplica autorización en backend, registra efectos auditables, rechaza estados o entradas inválidas.

        EN: Processes POST requests on ExternalLeadIngestAPIView using the api domain flow. It also preserves atomicity and explicit locking, enforces server-side authorization, records auditable effects, rejects invalid input or state.
        """

        client = getattr(request, "api_client", None)
        if not client:
            raise PermissionDenied("Este endpoint requiere autenticación mediante cliente API.")
        if not request.user.has_perm_code("leads.manage"):
            raise PermissionDenied("El usuario de servicio no puede crear leads.")
        key = request.headers.get("Idempotency-Key", "")
        try:
            record, replay = begin_idempotency(client=client, key=key, method=request.method, path=request.path, payload=request.data)
        except DjangoValidationError as exc:
            raise ValidationError(exc.messages if hasattr(exc, "messages") else str(exc)) from exc
        if replay:
            request._request._vinova_skip_generic_integration_log = True
            log_integration(
                direction=IntegrationLog.Direction.INBOUND,
                category="lead",
                action="lead.ingest.replay",
                status=IntegrationLog.Status.SUCCESS,
                client=client,
                user=request.user,
                branch=client.branch,
                endpoint=request.path,
                http_method=request.method,
                http_status=record.response_status,
                idempotency_key_hash=record.key_hash,
            )
            response = Response(record.response_body, status=record.response_status)
            response["Idempotency-Replayed"] = "true"
            return response
        request._request._vinova_skip_generic_integration_log = True
        serializer = ExternalLeadSerializer(data=request.data, context={"api_client": client})
        try:
            with transaction.atomic():
                serializer.is_valid(raise_exception=True)
                lead = serializer.save(created_by=request.user)
                body = {
                    "id": lead.pk,
                    "public_id": lead.public_id,
                    "code": lead.code,
                    "status": lead.status,
                    "created_at": lead.created_at,
                }
                complete_idempotency(record, response_status=201, response_body=body)
            log_integration(
                direction=IntegrationLog.Direction.INBOUND,
                category="lead",
                action="lead.ingest",
                status=IntegrationLog.Status.SUCCESS,
                client=client,
                user=request.user,
                branch=lead.branch,
                endpoint=request.path,
                http_method=request.method,
                http_status=201,
                payload=request.data,
                idempotency_key_hash=record.key_hash,
                metadata={"lead_id": lead.pk, "lead_code": lead.code},
            )
            audit_log(user=request.user, action="integrations.lead.ingest", target=lead, branch=lead.branch, metadata={"api_client": str(client.public_id)})
            return Response(body, status=201)
        except Exception as exc:
            fail_idempotency(record)
            log_integration(
                direction=IntegrationLog.Direction.INBOUND,
                category="lead",
                action="lead.ingest",
                status=IntegrationLog.Status.FAILED,
                client=client,
                user=request.user,
                branch=client.branch,
                endpoint=request.path,
                http_method=request.method,
                payload=request.data,
                idempotency_key_hash=record.key_hash,
                error_code="validation_or_create_failed",
                error_message=exc,
            )
            raise


class BIDatasetCatalogAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="vinova_bi_dataset_catalog",
        responses={200: BIDatasetCatalogResponseSerializer},
    )
    def get(self, request):
        if not (request.user.has_perm_code("analytics.export") or request.user.has_perm_code("data.export")):
            raise PermissionDenied("No tienes permiso para exportar datasets BI.")
        return Response({
            "schema_version": DATASET_VERSION,
            "datasets": [
                {"name": "sales", "contains_personal_data": False},
                {"name": "invoices", "contains_personal_data": False},
                {"name": "inventory", "contains_personal_data": False},
                {"name": "customers", "contains_personal_data": False, "note": "Dataset anonimizado."},
                {"name": "leads", "contains_personal_data": False, "note": "Sin datos de contacto."},
                {"name": "vehicles", "contains_personal_data": False},
            ],
            "filters": ["start_date", "end_date", "updated_since", "branch", "limit", "offset", "output"],
            "formats": ["json", "csv"],
            "max_limit": 5000,
        })


class BIDatasetAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="vinova_bi_dataset_retrieve",
        parameters=[
            OpenApiParameter("dataset", OpenApiTypes.STR, OpenApiParameter.PATH),
            OpenApiParameter("start_date", OpenApiTypes.DATE, OpenApiParameter.QUERY),
            OpenApiParameter("end_date", OpenApiTypes.DATE, OpenApiParameter.QUERY),
            OpenApiParameter("updated_since", OpenApiTypes.DATETIME, OpenApiParameter.QUERY),
            OpenApiParameter("branch", OpenApiTypes.INT, OpenApiParameter.QUERY),
            OpenApiParameter("limit", OpenApiTypes.INT, OpenApiParameter.QUERY),
            OpenApiParameter("offset", OpenApiTypes.INT, OpenApiParameter.QUERY),
            OpenApiParameter("output", OpenApiTypes.STR, OpenApiParameter.QUERY, enum=["json", "csv"]),
        ],
        responses={200: BIDatasetResponseSerializer},
    )
    def get(self, request, dataset):
        if not (request.user.has_perm_code("analytics.export") or request.user.has_perm_code("data.export")):
            raise PermissionDenied("No tienes permiso para exportar datasets BI.")
        try:
            data = dataset_rows(dataset, request)
        except KeyError as exc:
            raise ValidationError("Dataset no reconocido.") from exc
        client = getattr(request, "api_client", None)
        output_format = request.query_params.get("output", "json").lower()
        if output_format not in {"json", "csv"}:
            raise ValidationError({"output": "Usa json o csv."})
        request._request._vinova_skip_generic_integration_log = True
        log_integration(
            direction=IntegrationLog.Direction.OUTBOUND,
            category="bi",
            action=f"bi.{dataset}.read",
            status=IntegrationLog.Status.SUCCESS,
            client=client,
            user=request.user,
            branch=getattr(client, "branch", None),
            endpoint=request.path,
            http_method="GET",
            http_status=200,
            metadata={
                "count": data["count"],
                "offset": data["offset"],
                "schema_version": DATASET_VERSION,
                "format": output_format,
            },
        )
        if output_format == "csv":
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=data["columns"])
            writer.writeheader()
            writer.writerows(data["results"])
            response = HttpResponse(output.getvalue(), content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = f'attachment; filename="vinova_bi_{dataset}.csv"'
            response["X-Vinova-Schema-Version"] = DATASET_VERSION
            response["X-Total-Count"] = str(data["total"])
            return response
        return Response(data)


class AccountingExportAPIView(APIView):
    """ES: Agrupa el componente «accounting export a p i view» del dominio de API e integraciones y sus reglas relacionadas. Además, aplica autorización en backend, rechaza estados o entradas inválidas.

    EN: Groups the «accounting export a p i view» component and its related rules in the api domain. It also enforces server-side authorization, rejects invalid input or state.
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        operation_id="vinova_accounting_export",
        parameters=[
            OpenApiParameter("start_date", OpenApiTypes.DATE, OpenApiParameter.QUERY),
            OpenApiParameter("end_date", OpenApiTypes.DATE, OpenApiParameter.QUERY),
            OpenApiParameter("updated_since", OpenApiTypes.DATETIME, OpenApiParameter.QUERY),
            OpenApiParameter("branch", OpenApiTypes.INT, OpenApiParameter.QUERY),
            OpenApiParameter("limit", OpenApiTypes.INT, OpenApiParameter.QUERY),
            OpenApiParameter("offset", OpenApiTypes.INT, OpenApiParameter.QUERY),
            OpenApiParameter("output", OpenApiTypes.STR, OpenApiParameter.QUERY, enum=["json", "csv"]),
        ],
        responses={200: AccountingExportResponseSerializer},
    )
    def get(self, request):
        if not (request.user.has_perm_code("data.export") or request.user.has_perm_code("invoices.view")):
            raise PermissionDenied("No tienes permiso para exportar información contable.")
        rows, total, offset, limit = accounting_rows(request)
        fmt = request.query_params.get("output", "json").lower()
        if fmt not in {"json", "csv"}:
            raise ValidationError({"output": "Usa json o csv."})
        request._request._vinova_skip_generic_integration_log = True
        client = getattr(request, "api_client", None)
        log_integration(
            direction=IntegrationLog.Direction.OUTBOUND,
            category="accounting",
            action="accounting.export",
            status=IntegrationLog.Status.SUCCESS,
            client=client,
            user=request.user,
            branch=getattr(client, "branch", None),
            endpoint=request.path,
            http_method="GET",
            http_status=200,
            metadata={"format": fmt, "count": len(rows), "total": total},
        )
        if fmt == "csv":
            output = io.StringIO()
            fields = list(rows[0].keys()) if rows else [
                "id", "number", "invoice_type", "status", "issue_date", "company__ruc", "branch__code",
                "customer_document", "currency", "subtotal", "discount_total", "tax_total", "total",
                "authorization_number", "access_key", "updated_at",
            ]
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
            response = HttpResponse(output.getvalue(), content_type="text/csv; charset=utf-8")
            response["Content-Disposition"] = f'attachment; filename="vinova_contabilidad_{timezone.localdate().isoformat()}.csv"'
            return response
        return Response({
            "dataset": "accounting_documents",
            "schema_version": DATASET_VERSION,
            "generated_at": timezone.now(),
            "count": len(rows),
            "total": total,
            "offset": offset,
            "limit": limit,
            "results": rows,
        })
