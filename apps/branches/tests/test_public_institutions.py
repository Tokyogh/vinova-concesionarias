"""ES: Este módulo especifica regresiones ejecutables para el dominio de sucursales.

EN: This module specifies executable regressions for the branches domain.

Contexto existente / Existing context:
Regression coverage for public institutions in the branches domain.
"""

from decimal import Decimal
from io import BytesIO

import pytest
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.urls import reverse
from PIL import Image

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.audit.models import AuditLog
from apps.branches.forms import BranchForm
from apps.branches.models import Branch
from apps.branches.api.serializers import BranchSerializer
from apps.companies.models import Company
from apps.privacy.cookies import encode_cookie_preferences


pytestmark = pytest.mark.django_db


def make_test_image(name="sede.webp"):
    """ES: Genera imagen sintética válida. EN: Builds a valid synthetic image."""

    buffer = BytesIO()
    Image.new("RGB", (24, 16), color=(32, 126, 196)).save(buffer, format="WEBP")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/webp")


@pytest.fixture
def institution_company():
    return Company.objects.create(
        legal_name="Red Instituciones S.A.",
        commercial_name="Red Instituciones",
        ruc="1795555555001",
        is_active=True,
    )


def make_branch(company, *, code, name, branch_type, **overrides):
    values = {
        "company": company,
        "code": code,
        "name": name,
        "branch_type": branch_type,
        "city": "Quito",
        "province": "Pichincha",
        "address": "Av. Pública 123",
        "opening_hours": "Lunes a viernes",
        "services": ["Atención", "Asesoría"],
        "is_public": True,
        "is_active": True,
    }
    values.update(overrides)
    return Branch.objects.create(**values)


@pytest.fixture
def global_branch_manager(django_user_model):
    permission = PermissionCode.objects.create(
        module="branches",
        code="branches.manage",
        name="Gestionar sucursales",
    )
    role = Role.objects.create(code="branch_manager_test", name="Gestor global de sucursales", level=10)
    role.permissions.add(permission)
    user = django_user_model.objects.create_user(username="branch-manager", password="test-pass-123")
    UserRole.objects.create(user=user, role=role, branch=None)
    return user


def branch_payload(company, **overrides):
    values = {
        "company": company.pk,
        "name": "Institución E2E Quito",
        "code": "INST-E2E",
        "branch_type": Branch.BranchType.AFFILIATED_INSTITUTION,
        "city": "Quito",
        "province": "Pichincha",
        "address": "Dirección sintética E2E, Quito",
        "phone": "+593 2 000 0000",
        "email": "institucion-e2e@example.com",
        "description": "Sede sintética para verificar el flujo de publicación.",
        "opening_hours": "Lunes a viernes: 09h00 - 17h00",
        "website_url": "https://sede.example.com/informacion",
        "latitude": "-0.180653",
        "longitude": "-78.467834",
        "services_text": "Información de convenios\nAsesoría",
        "is_public": "on",
        "is_active": "on",
    }
    values.update(overrides)
    return values


def test_public_directory_exposes_only_active_public_supported_records(client, institution_company):
    visible = make_branch(
        institution_company,
        code="PUB-1",
        name="Institución visible",
        branch_type=Branch.BranchType.AFFILIATED_INSTITUTION,
        latitude=Decimal("-0.180653"),
        longitude=Decimal("-78.467834"),
    )
    make_branch(
        institution_company,
        code="PRIVATE",
        name="Sede privada",
        branch_type=Branch.BranchType.DEALERSHIP,
        is_public=False,
    )
    make_branch(
        institution_company,
        code="INACTIVE",
        name="Sede inactiva",
        branch_type=Branch.BranchType.SERVICE_CENTER,
        is_active=False,
    )
    make_branch(
        institution_company,
        code="WAREHOUSE",
        name="Bodega no comercial",
        branch_type=Branch.BranchType.WAREHOUSE,
    )

    response = client.get(reverse("institutions:list"))
    body = response.content.decode()

    assert response.status_code == 200
    assert list(response.context["institutions"]) == [visible]
    assert "Institución visible" in body
    assert "Sede privada" not in body
    assert "Sede inactiva" not in body
    assert "Bodega no comercial" not in body
    assert 'data-lat="-0.180653"' in body
    assert 'aria-current="page">Instituciones</a>' in body


def test_directory_counts_types_and_keeps_all_records_for_client_filters(client, institution_company):
    make_branch(institution_company, code="INST", name="Aliado", branch_type=Branch.BranchType.AFFILIATED_INSTITUTION)
    make_branch(institution_company, code="DEALER", name="Concesionario", branch_type=Branch.BranchType.DEALERSHIP)
    make_branch(institution_company, code="CARE", name="Atención", branch_type=Branch.BranchType.SERVICE_CENTER)

    response = client.get(reverse("institutions:list"), {"tipo": "dealership"})

    assert response.status_code == 200
    assert response.context["active_type"] == "dealership"
    assert response.context["institution_counts"] == {"institution": 1, "dealership": 1, "service_center": 1}
    assert len(response.context["institutions"]) == 3
    assert b'data-initial-type="dealership"' in response.content
    assert b"data-clear-institution-filters" in response.content
    assert b"Limpiar filtros" in response.content


def test_directory_rejects_unknown_filter_without_query_expansion(client, institution_company):
    make_branch(institution_company, code="INST", name="Aliado", branch_type=Branch.BranchType.AFFILIATED_INSTITUTION)

    response = client.get(reverse("institutions:list"), {"tipo": "<script>alert(1)</script>"})

    assert response.status_code == 200
    assert response.context["active_type"] == ""
    assert b"<script>alert(1)</script>" not in response.content


def test_directory_map_provider_is_optional_and_public_key_is_never_required(client, institution_company):
    make_branch(institution_company, code="MAP", name="Mapa", branch_type=Branch.BranchType.DEALERSHIP)

    with override_settings(MAPTILER_PUBLIC_KEY=""):
        without_key = client.get(reverse("institutions:list"))
    assert without_key.status_code == 200
    assert b"maplibre-gl.js" not in without_key.content
    assert b"MAPTILER_PUBLIC_KEY" not in without_key.content
    assert b"Mapa no disponible" in without_key.content

    with override_settings(MAPTILER_PUBLIC_KEY="public-browser-key"):
        without_consent = client.get(reverse("institutions:list"))
    assert b"maplibre-gl@4.7.1" not in without_consent.content
    assert b'public-browser-key' not in without_consent.content
    assert b"Preferencias de cookies" in without_consent.content

    client.cookies[settings.VINOVA_COOKIE_CONSENT_NAME] = encode_cookie_preferences(
        preferences=False,
        analytics=False,
        external_media=True,
    )
    with override_settings(MAPTILER_PUBLIC_KEY="public-browser-key"):
        with_key = client.get(reverse("institutions:list"))
    assert b"maplibre-gl@4.7.1" in with_key.content
    assert b'data-maptiler-key="public-browser-key"' in with_key.content


def test_branch_form_normalizes_public_services_without_changing_access_flags(institution_company):
    form = BranchForm(
        data={
            "company": institution_company.pk,
            "name": "Sede administrada",
            "code": "FORM-1",
            "branch_type": Branch.BranchType.SERVICE_CENTER,
            "city": "Cuenca",
            "province": "Azuay",
            "address": "Centro",
            "phone": "+593 7 000 0000",
            "email": "sede@example.com",
            "description": "Atención segura",
            "opening_hours": "09h00 - 17h00",
            "website_url": "https://sede.example.com",
            "latitude": "-2.900128",
            "longitude": "-79.005896",
            "services_text": "Atención, Garantías\nAtención; Repuestos",
            "is_public": True,
            "is_active": True,
        }
    )

    assert form.is_valid(), form.errors
    branch = form.save()
    assert branch.services == ["Atención", "Garantías", "Repuestos"]
    assert branch.is_public is True
    assert branch.is_active is True
    assert branch.website_url == "https://sede.example.com"


def test_branch_form_rejects_unsafe_website_scheme(institution_company):
    form = BranchForm(data=branch_payload(institution_company, website_url="javascript:alert(1)"))

    assert form.is_valid() is False
    assert "website_url" in form.errors


def test_inactive_company_hides_its_otherwise_public_branch(client):
    company = Company.objects.create(
        legal_name="Empresa Inactiva S.A.", commercial_name="Inactiva", ruc="1795555555002", is_active=False
    )
    make_branch(company, code="HIDDEN", name="No visible", branch_type=Branch.BranchType.DEALERSHIP)

    response = client.get(reverse("institutions:list"))

    assert response.status_code == 200
    assert list(response.context["institutions"]) == []
    assert b"No visible" not in response.content


def test_branch_api_rejects_non_list_services(institution_company):
    serializer = BranchSerializer(
        data={
            "company": institution_company.pk,
            "name": "Sede API",
            "code": "API-1",
            "branch_type": Branch.BranchType.DEALERSHIP,
            "city": "Quito",
            "services": {"unexpected": "shape"},
            "is_public": True,
            "is_active": True,
        }
    )

    assert serializer.is_valid() is False
    assert "services" in serializer.errors


def test_authorized_branch_management_publishes_updates_and_deactivates_audited_institution(
    client,
    institution_company,
    global_branch_manager,
    settings,
    tmp_path,
):
    settings.MEDIA_ROOT = tmp_path
    client.force_login(global_branch_manager)

    create_form = client.get(reverse("branches:create"))
    assert create_form.status_code == 200
    assert b'name="latitude"' in create_form.content
    assert b'name="services_text"' in create_form.content
    assert b'name="photo"' in create_form.content
    assert b'name="website_url"' in create_form.content

    create_values = branch_payload(institution_company)
    create_values["photo"] = make_test_image()
    created = client.post(reverse("branches:create"), create_values)
    branch = Branch.objects.get(code="INST-E2E")
    assert created.status_code == 302
    assert created.url == reverse("branches:detail", kwargs={"pk": branch.pk})
    assert branch.services == ["Información de convenios", "Asesoría"]
    assert branch.photo.name.startswith("branches/photos/")
    assert branch.website_url == "https://sede.example.com/informacion"
    creation_log = AuditLog.objects.get(action="branches.branch.create", object_id=str(branch.pk))
    assert creation_log.after["latitude"] == "-0.180653"
    assert creation_log.after["is_public"] is True
    assert creation_log.after["photo"] == branch.photo.name
    assert creation_log.after["website_url"] == "https://sede.example.com/informacion"

    published = client.get(reverse("institutions:list"))
    assert published.status_code == 200
    assert b"Instituci\xc3\xb3n E2E Quito" in published.content
    assert b'data-lat="-0.180653"' in published.content
    assert branch.photo.url.encode() in published.content
    assert b'href="https://sede.example.com/informacion"' in published.content

    update_values = branch_payload(
        institution_company,
        address="Dirección sintética E2E actualizada, Quito",
        latitude="-0.181000",
        longitude="-78.468000",
        services_text="Asesoría\nBeneficios afiliados",
        website_url="https://sede.example.com/contacto",
    )
    updated = client.post(reverse("branches:update", kwargs={"pk": branch.pk}), update_values)
    assert updated.status_code == 302
    branch.refresh_from_db()
    assert str(branch.latitude) == "-0.181000"
    assert branch.services == ["Asesoría", "Beneficios afiliados"]
    assert branch.website_url == "https://sede.example.com/contacto"
    update_log = AuditLog.objects.filter(action="branches.branch.update", object_id=str(branch.pk)).latest("occurred_at")
    assert update_log.before["latitude"] == "-0.180653"
    assert update_log.after["latitude"] == "-0.181000"
    assert update_log.before["website_url"] == "https://sede.example.com/informacion"
    assert update_log.after["website_url"] == "https://sede.example.com/contacto"

    republished = client.get(reverse("institutions:list"))
    assert b"Direcci\xc3\xb3n sint\xc3\xa9tica E2E actualizada" in republished.content
    assert b'data-lat="-0.181000"' in republished.content

    deactivated_values = branch_payload(institution_company)
    deactivated_values.pop("is_active")
    deactivated = client.post(
        reverse("branches:update", kwargs={"pk": branch.pk}),
        deactivated_values,
    )
    assert deactivated.status_code == 302
    branch.refresh_from_db()
    assert branch.is_active is False
    hidden = client.get(reverse("institutions:list"))
    assert b"Instituci\xc3\xb3n E2E Quito" not in hidden.content


def test_branch_management_rejects_authenticated_user_without_global_permission(
    client,
    django_user_model,
):
    user = django_user_model.objects.create_user(username="branch-denied", password="test-pass-123")
    client.force_login(user)

    assert client.get(reverse("branches:list")).status_code == 403
    assert client.get(reverse("branches:create")).status_code == 403
