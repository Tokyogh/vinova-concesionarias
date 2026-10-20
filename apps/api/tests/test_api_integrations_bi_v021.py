"""ES: Este módulo especifica regresiones ejecutables para el dominio de API e integraciones.

EN: This module specifies executable regressions for the api domain.

Contexto existente / Existing context:
Regression coverage for api integrations bi v021 in the api domain.
"""

from __future__ import annotations

from unittest.mock import Mock, patch

import pytest
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.management import call_command
from django.urls import resolve, reverse

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.api.models import (
    APIClient,
    APIScope,
    IdempotencyRecord,
    IntegrationLog,
    WebhookDelivery,
    WebhookEndpoint,
    WebhookEvent,
)
from apps.api.services import issue_api_client_token, issue_webhook_secret
from apps.api.tasks import deliver_webhook_task
from apps.api.validators import validate_webhook_url
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer
from apps.leads.models import Lead
from apps.vehicles.models import Vehicle, VehicleBrand, VehicleModel


@pytest.fixture
def api_context(django_user_model):
    company = Company.objects.create(
        legal_name="Vinova Integraciones S.A.",
        commercial_name="Vinova Integraciones",
        ruc="0990000001001",
    )
    branch_one = Branch.objects.create(
        company=company,
        name="Guayaquil Centro",
        code="gye-api",
        city="Guayaquil",
    )
    branch_two = Branch.objects.create(
        company=company,
        name="Quito Norte",
        code="uio-api",
        city="Quito",
    )
    admin = django_user_model.objects.create_user(
        username="api-admin",
        email="api-admin@example.com",
        password="pass12345",
        is_staff=True,
        is_superuser=True,
    )
    return {
        "company": company,
        "branch_one": branch_one,
        "branch_two": branch_two,
        "admin": admin,
    }


def grant_permissions(user, codes, *, branch=None):
    role = Role.objects.create(
        code=f"role-{user.username}-{Role.objects.count()}",
        name=f"Rol API {user.username}",
        level=20,
    )
    permissions = []
    for code in codes:
        permission, _ = PermissionCode.objects.get_or_create(
            code=code,
            defaults={"module": code.split(".", 1)[0], "name": code},
        )
        permissions.append(permission)
    role.permissions.set(permissions)
    UserRole.objects.create(user=user, role=role, branch=branch)
    return role


def api_credential(*, user, scopes, branch=None, name="Integración de pruebas"):
    client = APIClient.objects.create(
        name=name,
        service_user=user,
        branch=branch,
        allowed_ip_networks="127.0.0.1/32",
    )
    scope_objects = []
    for code in scopes:
        scope, _ = APIScope.objects.get_or_create(
            code=code,
            defaults={"name": code, "description": "Alcance de prueba"},
        )
        scope_objects.append(scope)
    client.scopes.set(scope_objects)
    token = issue_api_client_token(client, actor=user)
    return client, token


def auth_header(token):
    return {"HTTP_AUTHORIZATION": f"Bearer {token}"}


@pytest.mark.django_db
def test_seed_api_scopes_is_idempotent():
    call_command("seed_api_scopes")
    first_count = APIScope.objects.count()
    call_command("seed_api_scopes")
    assert first_count >= 30
    assert APIScope.objects.count() == first_count
    assert APIScope.objects.filter(code="bi:read", is_sensitive=True).exists()
    assert APIScope.objects.filter(code="accounting:export", is_sensitive=True).exists()


@pytest.mark.django_db
def test_api_client_token_is_hashed_authenticates_and_is_logged(client, api_context):
    api_client, token = api_credential(
        user=api_context["admin"],
        scopes=["api:read"],
    )
    raw_secret = token.split(".", 1)[1]
    assert raw_secret not in api_client.secret_digest

    response = client.get("/api/v1/meta/", **auth_header(token))

    assert response.status_code == 200
    assert response.json()["authenticated_as"] == "api_client"
    api_client.refresh_from_db()
    assert api_client.last_used_at is not None
    assert api_client.last_used_ip == "127.0.0.1"
    assert IntegrationLog.objects.filter(
        client=api_client,
        category="api",
        action="api.get",
        http_status=200,
    ).exists()


@pytest.mark.django_db
def test_invalid_or_missing_scope_is_rejected(client, api_context):
    _, token = api_credential(user=api_context["admin"], scopes=["api:read"])
    response = client.get("/api/v1/vehicles/", **auth_header(token))
    assert response.status_code == 403
    assert "vehicles:read" in str(response.json())

    bad = client.get("/api/v1/meta/", HTTP_AUTHORIZATION="Bearer vnp_invalid.secret")
    assert bad.status_code == 401


@pytest.mark.django_db
def test_branch_bound_api_client_only_reads_its_branch(client, api_context):
    brand = VehicleBrand.objects.create(name="Marca API")
    model = VehicleModel.objects.create(brand=brand, name="Modelo API")
    own_vehicle = Vehicle.objects.create(
        brand=brand,
        model=model,
        branch=api_context["branch_one"],
        year=2026,
        status=Vehicle.Status.AVAILABLE,
        price="30000.00",
        public_slug="marca-api-modelo-api-2026-gye",
    )
    Vehicle.objects.create(
        brand=brand,
        model=model,
        branch=api_context["branch_two"],
        year=2025,
        status=Vehicle.Status.AVAILABLE,
        price="25000.00",
        public_slug="marca-api-modelo-api-2025-uio",
    )
    _, token = api_credential(
        user=api_context["admin"],
        scopes=["vehicles:read", "companies:read"],
        branch=api_context["branch_one"],
    )

    response = client.get("/api/v1/vehicles/", **auth_header(token))

    assert response.status_code == 200
    ids = {row["id"] for row in response.json()["results"]}
    assert ids == {own_vehicle.pk}

    global_response = client.get("/api/v1/companies/", **auth_header(token))
    assert global_response.status_code == 403
    assert "recurso global" in str(global_response.json())


@pytest.mark.django_db
def test_write_scope_still_requires_write_permission(client, api_context, django_user_model):
    user = django_user_model.objects.create_user(
        username="vehicle-reader-api",
        email="vehicle-reader-api@example.com",
        password="x",
        branch=api_context["branch_one"],
    )
    grant_permissions(user, ["vehicles.view"], branch=api_context["branch_one"])
    _, token = api_credential(
        user=user,
        scopes=["vehicles:write"],
        branch=api_context["branch_one"],
    )

    response = client.post(
        "/api/v1/vehicles/",
        data={},
        content_type="application/json",
        **auth_header(token),
    )

    assert response.status_code == 403
    assert "permiso empresarial" in str(response.json())


@pytest.mark.django_db
def test_external_lead_ingestion_is_idempotent(client, api_context, django_user_model):
    user = django_user_model.objects.create_user(
        username="lead-service",
        email="lead-service@example.com",
        password="x",
        branch=api_context["branch_one"],
    )
    grant_permissions(user, ["leads.manage"], branch=api_context["branch_one"])
    api_client, token = api_credential(
        user=user,
        scopes=["leads:write"],
        branch=api_context["branch_one"],
    )
    payload = {
        "full_name": "Cliente de Integración",
        "email": "cliente.integracion@example.com",
        "phone": "0991112233",
        "city": "Guayaquil",
        "province": "Guayas",
        "message": "Solicita información",
        "consent_data_processing": True,
    }
    headers = {
        **auth_header(token),
        "HTTP_IDEMPOTENCY_KEY": "lead-external-0001",
    }

    first = client.post(
        "/api/v1/integrations/leads/",
        data=payload,
        content_type="application/json",
        **headers,
    )
    second = client.post(
        "/api/v1/integrations/leads/",
        data=payload,
        content_type="application/json",
        **headers,
    )

    assert first.status_code == 201
    assert second.status_code == 201
    assert second.headers["Idempotency-Replayed"] == "true"
    assert first.json()["id"] == second.json()["id"]
    assert Lead.objects.filter(email="cliente.integracion@example.com").count() == 1
    record = IdempotencyRecord.objects.get(client=api_client)
    assert record.status == IdempotencyRecord.Status.COMPLETED
    assert IntegrationLog.objects.filter(client=api_client, action="lead.ingest").exists()
    assert IntegrationLog.objects.filter(client=api_client, action="lead.ingest.replay").exists()

    changed = {**payload, "phone": "0980000000"}
    conflict = client.post(
        "/api/v1/integrations/leads/",
        data=changed,
        content_type="application/json",
        **headers,
    )
    assert conflict.status_code == 400
    assert Lead.objects.filter(email="cliente.integracion@example.com").count() == 1


@pytest.mark.django_db
def test_lead_ingestion_requires_idempotency_key(client, api_context, django_user_model):
    user = django_user_model.objects.create_user(
        username="lead-no-key",
        email="lead-no-key@example.com",
        password="x",
    )
    grant_permissions(user, ["leads.manage"])
    _, token = api_credential(user=user, scopes=["leads:write"])
    response = client.post(
        "/api/v1/integrations/leads/",
        data={"full_name": "Sin clave", "phone": "0999999999"},
        content_type="application/json",
        **auth_header(token),
    )
    assert response.status_code == 400
    assert Lead.objects.count() == 0


@pytest.mark.django_db
def test_bi_customer_dataset_is_branch_scoped_and_excludes_personal_data(client, api_context):
    own = Customer.objects.create(
        first_name="Ana",
        last_name="Segura",
        email="ana.secreta@example.com",
        phone="0991234567",
        identification_number="0912345678",
        city="Guayaquil",
        province="Guayas",
        assigned_branch=api_context["branch_one"],
    )
    Customer.objects.create(
        first_name="Otro",
        last_name="Cliente",
        email="otro@example.com",
        phone="0987654321",
        city="Quito",
        province="Pichincha",
        assigned_branch=api_context["branch_two"],
    )
    _, token = api_credential(
        user=api_context["admin"],
        scopes=["bi:read"],
        branch=api_context["branch_one"],
    )

    response = client.get("/api/v1/bi/customers/", **auth_header(token))

    assert response.status_code == 200
    payload = response.json()
    assert payload["schema_version"] == "1.0"
    assert payload["total"] == 1
    assert payload["results"][0]["id"] == own.pk
    serialized = response.content.decode("utf-8")
    assert "ana.secreta@example.com" not in serialized
    assert "0912345678" not in serialized
    assert "first_name" not in payload["columns"]
    assert "email" not in payload["columns"]

    csv_response = client.get("/api/v1/bi/customers/?output=csv", **auth_header(token))
    assert csv_response.status_code == 200
    assert csv_response["Content-Type"].startswith("text/csv")
    assert csv_response["X-Vinova-Schema-Version"] == "1.0"
    assert b"ana.secreta@example.com" not in csv_response.content


@pytest.mark.django_db
def test_bi_dataset_rejects_invalid_window(client, api_context):
    _, token = api_credential(user=api_context["admin"], scopes=["bi:read"])
    response = client.get("/api/v1/bi/sales/?start_date=not-a-date", **auth_header(token))
    assert response.status_code == 400
    assert "start_date" in response.json()


@pytest.mark.django_db
def test_api_client_management_is_session_only_and_secret_is_one_time(client, api_context):
    read_scope = APIScope.objects.create(code="integrations:read", name="Integraciones lectura")
    manage_scope = APIScope.objects.create(code="integrations:manage", name="Integraciones administración")
    client.force_login(api_context["admin"])
    response = client.post(
        "/api/v1/api-clients/",
        data={
            "name": "ERP principal",
            "description": "Conector contable",
            "service_user": api_context["admin"].pk,
            "branch": None,
            "scopes": [read_scope.code, manage_scope.code],
            "is_active": True,
            "allowed_ip_networks": "127.0.0.1/32",
            "rate_limit": "120/hour",
        },
        content_type="application/json",
    )
    assert response.status_code == 201
    token = response.json()["token"]
    stored = APIClient.objects.get(public_id=response.json()["public_id"])
    assert token not in stored.secret_digest
    assert stored.secret_last_four == token[-4:]

    client.logout()
    denied = client.get("/api/v1/api-clients/", **auth_header(token))
    assert denied.status_code == 403


@pytest.mark.django_db
def test_webhook_private_destinations_and_embedded_credentials_are_rejected():
    with pytest.raises(DjangoValidationError, match="privada|reservada"):
        validate_webhook_url("https://127.0.0.1/webhook")
    with pytest.raises(DjangoValidationError, match="credenciales"):
        validate_webhook_url("https://user:secret@example.com/webhook")


class FakeWebhookResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def getcode(self):
        return 204

    def read(self, size):  # noqa: ARG002
        return b"accepted"


@pytest.mark.django_db
def test_webhook_delivery_is_signed_and_marks_success(api_context):
    endpoint = WebhookEndpoint.objects.create(
        name="ERP webhook",
        url="https://hooks.example.test/vinova",
        event_types=["integration.test"],
        max_retries=3,
    )
    issue_webhook_secret(endpoint, actor=api_context["admin"])
    event = WebhookEvent.objects.create(
        event_type="integration.test",
        aggregate_type="test",
        aggregate_id="1",
        payload={"status": "ok"},
    )
    delivery = WebhookDelivery.objects.create(endpoint=endpoint, event=event)
    opener = Mock()
    opener.open.return_value = FakeWebhookResponse()

    with (
        patch("apps.api.tasks.validate_webhook_url"),
        patch("apps.api.tasks._webhook_opener", return_value=opener),
    ):
        result = deliver_webhook_task.run(delivery.pk)

    assert result == {"status": "succeeded", "code": 204}
    delivery.refresh_from_db()
    endpoint.refresh_from_db()
    assert delivery.status == WebhookDelivery.Status.SUCCEEDED
    assert delivery.attempts == 1
    assert delivery.delivered_at is not None
    assert endpoint.last_success_at is not None
    outbound_request = opener.open.call_args.args[0]
    headers = {key.lower(): value for key, value in outbound_request.header_items()}
    assert headers["x-vinova-signature"].startswith("v1=")
    assert headers["x-vinova-event"] == "integration.test"
    assert IntegrationLog.objects.filter(category="webhook", status=IntegrationLog.Status.SUCCESS).exists()


@pytest.mark.django_db
def test_v1_schema_and_routes_are_connected(client, api_context):
    client.force_login(api_context["admin"])
    assert reverse("api_v1:meta") == "/api/v1/meta/"
    assert resolve("/api/v1/integrations/leads/").url_name == "integration-lead-ingest"
    schema = client.get("/api/v1/schema/")
    assert schema.status_code == 200
    assert b"/api/v1/meta/" in schema.content


@pytest.mark.django_db
def test_branch_scoped_session_user_only_reads_integration_logs_from_own_branch(client, api_context, django_user_model):
    user = django_user_model.objects.create_user(
        username="branch-integration-auditor",
        email="branch-integration-auditor@example.com",
        password="pass12345",
        branch=api_context["branch_one"],
    )
    grant_permissions(user, ["integrations.view"], branch=api_context["branch_one"])
    own = IntegrationLog.objects.create(
        direction=IntegrationLog.Direction.INBOUND,
        category="api",
        action="own.branch",
        status=IntegrationLog.Status.SUCCESS,
        branch=api_context["branch_one"],
    )
    IntegrationLog.objects.create(
        direction=IntegrationLog.Direction.INBOUND,
        category="api",
        action="other.branch",
        status=IntegrationLog.Status.SUCCESS,
        branch=api_context["branch_two"],
    )

    client.force_login(user)
    response = client.get("/api/v1/integration-logs/")

    assert response.status_code == 200
    ids = {row["public_id"] for row in response.json()["results"]}
    assert ids == {str(own.public_id)}


@pytest.mark.django_db
def test_branch_scoped_session_manager_cannot_create_global_or_other_branch_client(client, api_context, django_user_model):
    manager = django_user_model.objects.create_user(
        username="branch-integration-manager",
        email="branch-integration-manager@example.com",
        password="pass12345",
        branch=api_context["branch_one"],
    )
    service_user = django_user_model.objects.create_user(
        username="branch-service-user",
        email="branch-service-user@example.com",
        password="pass12345",
        branch=api_context["branch_one"],
    )
    grant_permissions(
        manager,
        ["integrations.view", "integrations.manage"],
        branch=api_context["branch_one"],
    )
    scope = APIScope.objects.create(code="api:read", name="API lectura")
    client.force_login(manager)

    response = client.post(
        "/api/v1/api-clients/",
        data={
            "name": "Cliente fuera de alcance",
            "service_user": service_user.pk,
            "branch": api_context["branch_two"].pk,
            "scopes": [scope.code],
            "is_active": True,
            "allowed_ip_networks": "127.0.0.1/32",
            "rate_limit": "60/hour",
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    assert "branch" in response.json()
    assert APIClient.objects.filter(name="Cliente fuera de alcance").count() == 0


@pytest.mark.django_db
def test_api_client_ip_allowlist_uses_trusted_proxy_ip(client, api_context, settings):
    settings.VINOVA_TRUST_PROXY_HEADERS = True
    api_client = APIClient.objects.create(
        name="Integración IP pública",
        service_user=api_context["admin"],
        allowed_ip_networks="203.0.113.40/32",
    )
    scope = APIScope.objects.create(code="api:read", name="API lectura por IP")
    api_client.scopes.add(scope)
    token = issue_api_client_token(api_client, actor=api_context["admin"])

    response = client.get(
        "/api/v1/meta/",
        HTTP_AUTHORIZATION=f"Bearer {token}",
        HTTP_X_FORWARDED_FOR="203.0.113.40",
        REMOTE_ADDR="172.20.0.5",
    )

    assert response.status_code == 200
    api_client.refresh_from_db()
    assert api_client.last_used_ip == "203.0.113.40"


@pytest.mark.django_db
def test_expired_idempotency_key_can_be_reused_with_a_new_payload(client, api_context, django_user_model):
    from django.utils import timezone

    user = django_user_model.objects.create_user(
        username="lead-expired-key",
        email="lead-expired-key@example.com",
        password="x",
        branch=api_context["branch_one"],
    )
    grant_permissions(user, ["leads.manage"], branch=api_context["branch_one"])
    api_client, token = api_credential(
        user=user,
        scopes=["leads:write"],
        branch=api_context["branch_one"],
    )
    headers = {**auth_header(token), "HTTP_IDEMPOTENCY_KEY": "reusable-after-ttl"}
    first = client.post(
        "/api/v1/integrations/leads/",
        data={"full_name": "Primer lead", "phone": "0991111111"},
        content_type="application/json",
        **headers,
    )
    assert first.status_code == 201
    IdempotencyRecord.objects.filter(client=api_client).update(
        expires_at=timezone.now() - timezone.timedelta(seconds=1)
    )

    second = client.post(
        "/api/v1/integrations/leads/",
        data={"full_name": "Segundo lead", "phone": "0992222222"},
        content_type="application/json",
        **headers,
    )

    assert second.status_code == 201
    assert second.json()["id"] != first.json()["id"]
    assert Lead.objects.filter(full_name__in=["Primer lead", "Segundo lead"]).count() == 2
