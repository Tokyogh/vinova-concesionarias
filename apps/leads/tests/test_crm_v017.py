"""ES: Este módulo especifica regresiones ejecutables para el dominio de CRM y leads.

EN: This module specifies executable regressions for the leads domain.

Contexto existente / Existing context:
Regression coverage for crm v017 in the leads domain.
"""

from datetime import timedelta
from io import BytesIO

import pytest
from django.conf import settings
from django.utils import timezone
from openpyxl import load_workbook

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.analytics.models import VehicleInteraction
from apps.audit.models import AuditLog
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer, CustomerVehicleInterest
from apps.leads.models import Lead, LeadActivity, TestDrive as LeadTestDrive
from apps.privacy.cookies import encode_cookie_preferences
from apps.sales.models import SaleRecord
from apps.vehicles.models import Vehicle, VehicleBrand, VehicleModel


@pytest.fixture
def crm_context(django_user_model):
    company = Company.objects.create(legal_name="Vinova Ecuador S.A.", commercial_name="Vinova", ruc="0998887776001")
    branch = Branch.objects.create(company=company, name="Quito Norte", code="quito-norte-crm", city="Quito")
    brand = VehicleBrand.objects.create(name="Foton CRM")
    model = VehicleModel.objects.create(brand=brand, name="Tunland CRM")
    vehicle = Vehicle.objects.create(
        brand=brand,
        model=model,
        branch=branch,
        year=2026,
        price="39990.00",
        status=Vehicle.Status.AVAILABLE,
        public_slug="foton-tunland-crm-2026",
        published_at=timezone.now(),
    )
    user = django_user_model.objects.create_user(
        username="crmmanager", email="crmmanager@example.com", password="pass12345", branch=branch,
    )
    codes = [
        "dashboard.view", "leads.view", "leads.manage", "leads.assign", "leads.export",
        "analytics.view", "analytics.export", "sales.quote", "customers.view", "customers.manage", "vehicles.view",
    ]
    permissions = [PermissionCode.objects.create(module=code.split(".")[0], code=code, name=code) for code in codes]
    role = Role.objects.create(code="crm-manager-test", name="CRM Manager", level=5)
    role.permissions.set(permissions)
    UserRole.objects.create(user=user, role=role)
    return {"company": company, "branch": branch, "vehicle": vehicle, "user": user}


@pytest.mark.django_db
def test_public_vehicle_request_creates_lead_and_privacy_safe_interactions(client, crm_context):
    vehicle = crm_context["vehicle"]
    client.cookies[settings.VINOVA_COOKIE_CONSENT_NAME] = encode_cookie_preferences(
        preferences=False,
        analytics=True,
        external_media=False,
    )
    get_response = client.get(f"/leads/request/vehicle/{vehicle.pk}/")
    assert get_response.status_code == 200
    assert VehicleInteraction.objects.filter(event_type=VehicleInteraction.EventType.INFO_CLICK, vehicle=vehicle).count() == 1

    response = client.post(
        f"/leads/request/vehicle/{vehicle.pk}/",
        {
            "request_type": Lead.RequestType.QUOTE,
            "full_name": "Ana Torres",
            "email": "ANA@EXAMPLE.COM",
            "phone": "0990000000",
            "whatsapp": "0990000000",
            "preferred_contact_method": "whatsapp",
            "city": "Quito",
            "province": "Pichincha",
            "budget_min": "30000.00",
            "budget_max": "45000.00",
            "expected_purchase_date": "",
            "message": "Deseo una cotización con financiamiento.",
            "consent_data_processing": "on",
            "website": "",
        },
    )
    lead = Lead.objects.get(full_name="Ana Torres")
    assert response.status_code == 302
    assert str(lead.public_id) in response.headers["Location"]
    assert lead.code.startswith("LEAD-")
    assert lead.email == "ana@example.com"
    assert lead.vehicle == vehicle
    assert lead.branch == vehicle.branch
    assert lead.consent_data_processing is True
    assert lead.consent_at is not None
    assert lead.ip_hash and lead.session_hash
    assert "127.0.0.1" not in lead.ip_hash
    assert lead.score > 50
    assert VehicleInteraction.objects.filter(lead=lead, event_type=VehicleInteraction.EventType.QUOTE_REQUEST).exists()
    assert LeadActivity.objects.filter(lead=lead).exists()


@pytest.mark.django_db
def test_public_form_rejects_missing_contact(client):
    response = client.post(
        "/leads/request/",
        {
            "request_type": Lead.RequestType.INFORMATION,
            "full_name": "Persona sin contacto",
            "email": "",
            "phone": "",
            "whatsapp": "",
            "preferred_contact_method": "whatsapp",
            "city": "Cuenca",
            "province": "Azuay",
            "message": "Consulta",
            "consent_data_processing": "on",
            "website": "",
        },
    )
    assert response.status_code == 400
    assert Lead.objects.count() == 0


@pytest.mark.django_db
def test_crm_list_pipeline_and_detail_require_permission(client, crm_context, django_user_model):
    lead = Lead.objects.create(full_name="Lead Visible", phone="0991111111", branch=crm_context["branch"])
    no_perm = django_user_model.objects.create_user(username="noperm", email="noperm@example.com", password="x")
    client.force_login(no_perm)
    assert client.get("/dashboard/leads/").status_code == 403

    client.force_login(crm_context["user"])
    response = client.get("/dashboard/leads/")
    assert response.status_code == 200
    assert lead.code.encode() in response.content
    assert client.get("/dashboard/leads/pipeline/").status_code == 200
    detail = client.get(f"/dashboard/leads/{lead.pk}/")
    assert detail.status_code == 200
    assert b"Historial comercial" in detail.content


@pytest.mark.django_db
def test_status_assignment_activity_and_test_drive_flow(client, crm_context):
    user = crm_context["user"]
    lead = Lead.objects.create(full_name="Carlos Ruiz", phone="0987654321", branch=crm_context["branch"], vehicle=crm_context["vehicle"])
    client.force_login(user)

    response = client.post(
        f"/dashboard/leads/{lead.pk}/assign/",
        {"branch": crm_context["branch"].pk, "assigned_advisor": user.pk, "note": "Asignación inicial"},
    )
    assert response.status_code == 302
    lead.refresh_from_db()
    assert lead.assigned_advisor == user

    response = client.post(
        f"/dashboard/leads/{lead.pk}/status/",
        {"status": Lead.Status.CONTACTED, "note": "Cliente respondió", "lost_reason": "", "next_follow_up_at": ""},
    )
    lead.refresh_from_db()
    assert lead.status == Lead.Status.CONTACTED
    assert LeadActivity.objects.filter(lead=lead, activity_type=LeadActivity.ActivityType.STATUS).exists()

    start = timezone.localtime(timezone.now() + timedelta(days=1)).replace(second=0, microsecond=0)
    end = start + timedelta(hours=1)
    response = client.post(
        f"/dashboard/leads/{lead.pk}/test-drive/",
        {
            "vehicle": crm_context["vehicle"].pk,
            "branch": crm_context["branch"].pk,
            "advisor": user.pk,
            "starts_at": start.strftime("%Y-%m-%dT%H:%M"),
            "ends_at": end.strftime("%Y-%m-%dT%H:%M"),
            "status": LeadTestDrive.Status.SCHEDULED,
            "notes": "Ruta urbana",
        },
    )
    assert response.status_code == 302
    lead.refresh_from_db()
    assert lead.status == Lead.Status.TEST_DRIVE
    assert LeadTestDrive.objects.filter(lead=lead).count() == 1


@pytest.mark.django_db
def test_lost_status_requires_reason(client, crm_context):
    lead = Lead.objects.create(full_name="Lead Perdible", phone="0900000000", branch=crm_context["branch"])
    client.force_login(crm_context["user"])
    client.post(f"/dashboard/leads/{lead.pk}/status/", {"status": Lead.Status.LOST, "note": "", "lost_reason": "", "next_follow_up_at": ""})
    lead.refresh_from_db()
    assert lead.status == Lead.Status.NEW

    client.post(f"/dashboard/leads/{lead.pk}/status/", {"status": Lead.Status.LOST, "note": "", "lost_reason": "Compró en otra concesionaria", "next_follow_up_at": ""})
    lead.refresh_from_db()
    assert lead.status == Lead.Status.LOST
    assert lead.closed_at is not None
    assert lead.lost_reason == "Compró en otra concesionaria"


@pytest.mark.django_db
def test_convert_to_customer_and_create_quote(client, crm_context):
    lead = Lead.objects.create(
        full_name="María López", email="maria@example.com", phone="0977777777", city="Quito",
        province="Pichincha", branch=crm_context["branch"], vehicle=crm_context["vehicle"],
        assigned_advisor=crm_context["user"], request_type=Lead.RequestType.QUOTE,
    )
    client.force_login(crm_context["user"])
    response = client.post(f"/dashboard/leads/{lead.pk}/create-quote/")
    assert response.status_code == 302
    lead.refresh_from_db()
    assert lead.customer is not None
    assert lead.linked_sale is not None
    assert lead.status == Lead.Status.QUOTED
    assert lead.linked_sale.kind == SaleRecord.Kind.QUOTE
    assert lead.linked_sale.customer == lead.customer
    assert CustomerVehicleInterest.objects.filter(customer=lead.customer, vehicle=lead.vehicle).exists()


@pytest.mark.django_db
def test_analytics_dashboard_export_profiles_and_api(client, crm_context):
    user = crm_context["user"]
    customer = Customer.objects.create(first_name="Elena", last_name="Paz", email="elena@example.com", phone="0966666666", assigned_branch=crm_context["branch"], assigned_advisor=user)
    lead = Lead.objects.create(
        full_name="Elena Paz", email=customer.email, phone=customer.phone, city="Quito", province="Pichincha",
        branch=crm_context["branch"], vehicle=crm_context["vehicle"], assigned_advisor=user, customer=customer,
        status=Lead.Status.WON, source=Lead.Source.WEB_CATALOG,
    )
    client.force_login(user)

    dashboard = client.get("/dashboard/analytics/")
    assert dashboard.status_code == 200
    assert b"Embudo comercial" in dashboard.content
    export = client.get("/dashboard/analytics/export/")
    assert export.status_code == 200
    workbook = load_workbook(BytesIO(export.content))
    assert "leads_dataset" in workbook.sheetnames
    assert "vehicles" in workbook.sheetnames

    assert client.get(f"/dashboard/customers/{customer.pk}/profile/").status_code == 200
    assert client.get(f"/dashboard/users/{user.pk}/profile/").status_code == 200

    summary = client.get("/api/commercial-analytics/summary/")
    assert summary.status_code == 200
    assert summary.json()["metrics"]["total"] >= 1
    leads_api = client.get("/api/leads/")
    assert leads_api.status_code == 200
    assert any(row["code"] == lead.code for row in leads_api.json()["results"])


@pytest.mark.django_db
def test_branch_assignment_limits_leads_forms_api_and_analytics(client, crm_context, django_user_model):
    user = crm_context["user"]
    own_branch = crm_context["branch"]
    assignment = user.user_roles.get()
    assignment.branch = own_branch
    assignment.save(update_fields=["branch", "updated_at"])
    assignment.role.code = "gerente_comercial"
    assignment.role.save(update_fields=["code", "updated_at"])

    other_branch = Branch.objects.create(
        company=crm_context["company"], name="Guayaquil CRM", code="guayaquil-crm", city="Guayaquil"
    )
    other_vehicle = Vehicle.objects.create(
        brand=crm_context["vehicle"].brand,
        model=crm_context["vehicle"].model,
        branch=other_branch,
        year=2025,
        price="35990.00",
        status=Vehicle.Status.AVAILABLE,
        public_slug="foton-tunland-crm-2025",
    )
    other_advisor = django_user_model.objects.create_user(
        username="crm-other", email="crm-other@example.com", password="x", branch=other_branch
    )
    UserRole.objects.create(user=other_advisor, role=assignment.role, branch=other_branch)
    own_customer = Customer.objects.create(first_name="Cliente CRM propio", assigned_branch=own_branch)
    other_customer = Customer.objects.create(first_name="Cliente CRM ajeno", assigned_branch=other_branch)
    own_lead = Lead.objects.create(full_name="Lead CRM propio", phone="0991000001", branch=own_branch)
    other_lead = Lead.objects.create(full_name="Lead CRM ajeno", phone="0991000002", branch=other_branch)
    unassigned_lead = Lead.objects.create(full_name="Lead CRM sin sucursal", phone="0991000003")
    client.force_login(user)

    html = client.get("/dashboard/leads/")
    assert html.status_code == 200
    assert [lead.pk for lead in html.context["leads"]] == [own_lead.pk]
    assert html.context["metrics"]["total"] == 1
    assert list(html.context["filter_form"].fields["branch"].queryset) == [own_branch]
    assert client.get(f"/dashboard/leads/{other_lead.pk}/").status_code == 404
    assert client.get(f"/dashboard/leads/{unassigned_lead.pk}/").status_code == 404
    assert client.post(
        f"/dashboard/leads/{other_lead.pk}/status/",
        {"status": Lead.Status.CONTACTED, "lost_reason": "", "next_follow_up_at": ""},
    ).status_code == 404

    client.post(
        f"/dashboard/leads/{own_lead.pk}/assign/",
        {"branch": other_branch.pk, "assigned_advisor": other_advisor.pk, "note": "No permitido"},
    )
    own_lead.refresh_from_db()
    assert own_lead.branch == own_branch
    assert own_lead.assigned_advisor is None

    create_form = client.get("/dashboard/leads/new/").context["form"]
    assert list(create_form.fields["branch"].queryset) == [own_branch]
    assert list(create_form.fields["customer"].queryset) == [own_customer]
    assert list(create_form.fields["vehicle"].queryset) == [crm_context["vehicle"]]
    assert list(create_form.fields["assigned_advisor"].queryset) == [user]
    assert create_form.fields["branch"].required is True

    api = client.get("/api/v1/leads/")
    assert api.status_code == 200
    assert [lead["id"] for lead in api.json()["results"]] == [own_lead.pk]
    assert client.get(f"/api/v1/leads/{other_lead.pk}/").status_code == 404
    invalid_lead = client.post(
        "/api/v1/leads/",
        {"full_name": "Lead fuera de alcance", "phone": "0991000004", "branch": other_branch.pk},
        content_type="application/json",
    )
    assert invalid_lead.status_code == 400
    assert "branch" in invalid_lead.json()
    invalid_activity = client.post(
        "/api/v1/lead-activities/",
        {"lead": other_lead.pk, "activity_type": LeadActivity.ActivityType.NOTE, "title": "No permitido"},
        content_type="application/json",
    )
    assert invalid_activity.status_code == 400
    assert "lead" in invalid_activity.json()

    analytics = client.get("/dashboard/analytics/")
    assert analytics.status_code == 200
    assert analytics.context["metrics"]["total"] == 1
    assert list(analytics.context["filter_form"].fields["branch"].queryset) == [own_branch]
    assert client.get(f"/dashboard/users/{other_advisor.pk}/profile/").status_code == 404

    assignment.branch = None
    assignment.save(update_fields=["branch", "updated_at"])
    global_api = client.get("/api/v1/leads/")
    assert global_api.status_code == 200
    assert {lead["id"] for lead in global_api.json()["results"]} == {
        own_lead.pk,
        other_lead.pk,
        unassigned_lead.pk,
    }
    assert other_customer.pk not in set(create_form.fields["customer"].queryset.values_list("pk", flat=True))
    assert other_vehicle.pk not in set(create_form.fields["vehicle"].queryset.values_list("pk", flat=True))

    assignment.expires_at = timezone.now()
    assignment.save(update_fields=["expires_at", "updated_at"])
    assert client.get("/dashboard/leads/").status_code == 403
    assert client.get("/api/v1/leads/").status_code == 403


@pytest.mark.django_db
def test_branch_salesperson_keeps_ownership_scope(client, crm_context, django_user_model):
    branch = crm_context["branch"]
    seller = django_user_model.objects.create_user(
        username="crm-seller", email="crm-seller@example.com", password="x", branch=branch
    )
    role = Role.objects.create(code="vendedor", name="Vendedor CRM")
    role.permissions.add(PermissionCode.objects.get(code="leads.view"))
    UserRole.objects.create(user=seller, role=role, branch=branch)
    own = Lead.objects.create(full_name="Lead vendedor", phone="0992000001", branch=branch, assigned_advisor=seller)
    unassigned = Lead.objects.create(full_name="Lead libre", phone="0992000002", branch=branch)
    other = Lead.objects.create(
        full_name="Lead de otro asesor",
        phone="0992000003",
        branch=branch,
        assigned_advisor=crm_context["user"],
    )
    client.force_login(seller)

    response = client.get("/api/v1/leads/")

    assert response.status_code == 200
    assert {lead["id"] for lead in response.json()["results"]} == {own.pk, unassigned.pk}
    assert other.pk not in {lead["id"] for lead in response.json()["results"]}


@pytest.mark.django_db
def test_crm_api_uses_services_and_keeps_history_append_only(client, crm_context, django_user_model):
    user = crm_context["user"]
    client.force_login(user)

    created = client.post(
        "/api/v1/leads/",
        {
            "full_name": "Lead API seguro",
            "phone": "0993000001",
            "branch": crm_context["branch"].pk,
            "vehicle": crm_context["vehicle"].pk,
            "status": Lead.Status.WON,
            "closed_at": timezone.now().isoformat(),
        },
        content_type="application/json",
    )
    assert created.status_code == 201
    lead = Lead.objects.get(pk=created.json()["id"])
    assert lead.status == Lead.Status.NEW
    assert lead.closed_at is None
    assert lead.created_by == user
    assert lead.assigned_advisor == user
    assert lead.score > 0
    assert LeadActivity.objects.filter(lead=lead, activity_type=LeadActivity.ActivityType.SYSTEM).exists()
    assert AuditLog.objects.filter(action="leads.create", object_id=str(lead.pk)).exists()
    assert client.patch(
        f"/api/v1/leads/{lead.pk}/", {"status": Lead.Status.WON}, content_type="application/json"
    ).status_code == 405
    assert client.put(
        f"/api/v1/leads/{lead.pk}/", {"full_name": "Reemplazo"}, content_type="application/json"
    ).status_code == 405
    assert client.delete(f"/api/v1/leads/{lead.pk}/").status_code == 405

    completed_at = timezone.now()
    activity = client.post(
        "/api/v1/lead-activities/",
        {
            "lead": lead.pk,
            "activity_type": LeadActivity.ActivityType.CALL,
            "title": "Llamada API",
            "completed_at": completed_at.isoformat(),
            "previous_status": Lead.Status.LOST,
            "metadata": {"forged": True},
        },
        content_type="application/json",
    )
    assert activity.status_code == 201
    activity_record = LeadActivity.objects.get(pk=activity.json()["id"])
    assert activity_record.created_by == user
    assert activity_record.previous_status == ""
    assert activity_record.metadata == {}
    lead.refresh_from_db()
    assert lead.last_contact_at is not None
    assert client.patch(
        f"/api/v1/lead-activities/{activity_record.pk}/",
        {"detail": "Alterado"},
        content_type="application/json",
    ).status_code == 405
    assert client.delete(f"/api/v1/lead-activities/{activity_record.pk}/").status_code == 405

    starts_at = timezone.now() + timedelta(days=1)
    test_drive = client.post(
        "/api/v1/test-drives/",
        {
            "lead": lead.pk,
            "vehicle": crm_context["vehicle"].pk,
            "branch": crm_context["branch"].pk,
            "advisor": user.pk,
            "starts_at": starts_at.isoformat(),
            "ends_at": (starts_at + timedelta(hours=1)).isoformat(),
            "status": LeadTestDrive.Status.COMPLETED,
            "result_notes": "Resultado falsificado",
            "notes": "Ruta API",
        },
        content_type="application/json",
    )
    assert test_drive.status_code == 201
    test_drive_record = LeadTestDrive.objects.get(pk=test_drive.json()["id"])
    assert test_drive_record.status == LeadTestDrive.Status.SCHEDULED
    assert test_drive_record.result_notes == ""
    assert test_drive_record.created_by == user
    lead.refresh_from_db()
    assert lead.status == Lead.Status.TEST_DRIVE
    assert client.patch(
        f"/api/v1/test-drives/{test_drive_record.pk}/",
        {"status": LeadTestDrive.Status.COMPLETED},
        content_type="application/json",
    ).status_code == 405
    assert client.delete(f"/api/v1/test-drives/{test_drive_record.pk}/").status_code == 405

    viewer = django_user_model.objects.create_user(
        username="crm-api-viewer", email="crm-api-viewer@example.com", password="x"
    )
    viewer_role = Role.objects.create(code="crm-api-viewer", name="Consulta CRM API")
    viewer_role.permissions.add(PermissionCode.objects.get(code="leads.view"))
    UserRole.objects.create(user=viewer, role=viewer_role, branch=crm_context["branch"])
    client.force_login(viewer)
    assert client.post(
        "/api/v1/lead-activities/",
        {"lead": lead.pk, "activity_type": LeadActivity.ActivityType.NOTE, "title": "No autorizado"},
        content_type="application/json",
    ).status_code == 403


@pytest.mark.django_db
def test_superuser_without_userrole_can_create_internal_lead(client, crm_context, django_user_model):
    admin = django_user_model.objects.create_superuser(
        username="leaf_admin", email="leaf-admin@example.com", password="x", branch=crm_context["branch"]
    )
    client.force_login(admin)
    response = client.post(
        "/dashboard/leads/new/",
        {
            "request_type": Lead.RequestType.QUOTE,
            "status": Lead.Status.NEW,
            "priority": Lead.Priority.HIGH,
            "source": Lead.Source.SHOWROOM,
            "full_name": "Prospecto Regresión",
            "email": "prospecto.regresion@example.com",
            "branch": str(crm_context["branch"].pk),
        },
    )
    assert response.status_code == 302
    lead = Lead.objects.get(email="prospecto.regresion@example.com")
    assert lead.assigned_advisor == admin
