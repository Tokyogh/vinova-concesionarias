"""ES: Este módulo especifica regresiones ejecutables para el dominio de portal cliente.

EN: This module specifies executable regressions for the portal domain.

Contexto existente / Existing context:
Regression coverage for portal in the portal domain.
"""

from datetime import timedelta

import pytest
from django.test import Client, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer
from apps.notifications.models import NotificationMessage, NotificationRecipient
from apps.security_center.services import get_security_profile
from apps.vehicles.models import (
    CustomerVehicle,
    Vehicle,
    VehicleBrand,
    VehicleLinkCode,
    VehicleMedia,
    VehicleModel,
    VehicleResource,
)
from apps.vehicles.services import generate_vehicle_link_code


@pytest.fixture
def portal_permission(db):
    permission, _ = PermissionCode.objects.update_or_create(
        code="portal.access", defaults={"module": "portal", "name": "Acceso al portal"}
    )
    role, _ = Role.objects.update_or_create(
        code="cliente", defaults={"name": "Cliente", "level": 100, "is_active": True}
    )
    role.permissions.add(permission)
    return role


@pytest.fixture
def portal_context(django_user_model, portal_permission):
    user = django_user_model.objects.create_user(
        username="portal-client", email="portal-client@example.com", password="VinovaCliente2026!"
    )
    UserRole.objects.create(user=user, role=portal_permission)
    customer = Customer.objects.create(
        first_name="Ana",
        last_name="Portal",
        identification_type=Customer.IdentificationType.CEDULA,
        identification_number="0911453215",
        email=user.email,
        phone="0990000001",
        status=Customer.Status.ACTIVE,
        account=user,
    )
    get_security_profile(user)
    return user, customer


@pytest.mark.django_db
def test_portal_requires_authentication(client):
    response = client.get(reverse("portal:dashboard"))
    assert response.status_code == 302
    assert reverse("accounts:login") in response.url


@pytest.mark.django_db
def test_portal_rejects_user_without_permission(client, django_user_model):
    user = django_user_model.objects.create_user(username="plain", email="plain@example.com", password="x")
    client.force_login(user)
    assert client.get(reverse("portal:dashboard")).status_code == 403


@pytest.mark.django_db
def test_portal_does_not_grant_staff_implicit_client_access(client, django_user_model):
    staff = django_user_model.objects.create_user(
        username="staff-without-client-role",
        email="staff-without-client-role@example.com",
        password="x",
        is_staff=True,
    )
    Customer.objects.create(
        first_name="Staff",
        email=staff.email,
        account=staff,
        status=Customer.Status.ACTIVE,
    )
    client.force_login(staff)

    assert client.get(reverse("portal:dashboard")).status_code == 403


@pytest.mark.django_db
def test_portal_shows_controlled_page_when_customer_link_is_missing(client, django_user_model, portal_permission):
    user = django_user_model.objects.create_user(username="orphan-client", email="orphan@example.com", password="x")
    UserRole.objects.create(user=user, role=portal_permission)
    client.force_login(user)
    response = client.get(reverse("portal:dashboard"))

    assert response.status_code == 409
    content = response.content.decode()
    assert "necesita vinculación o activación" in content
    assert "no intentamos asociar expedientes automáticamente" in content
    assert "PortalDashboardView" not in content


@pytest.mark.django_db
@pytest.mark.parametrize("status", (Customer.Status.INACTIVE, Customer.Status.ARCHIVED))
def test_portal_shows_controlled_page_for_ineligible_customer_status(client, portal_context, status):
    user, customer = portal_context
    customer.status = status
    customer.save(update_fields=["status", "updated_at"])
    client.force_login(user)

    response = client.get(reverse("portal:dashboard"))

    assert response.status_code == 409
    assert "necesita vinculación o activación" in response.content.decode()


@pytest.mark.django_db
def test_portal_shows_controlled_page_for_soft_deleted_customer(client, portal_context):
    user, customer = portal_context
    customer.is_deleted = True
    customer.deleted_at = timezone.now()
    customer.save(update_fields=["is_deleted", "deleted_at", "updated_at"])
    client.force_login(user)

    assert client.get(reverse("portal:dashboard")).status_code == 409


@pytest.mark.django_db
def test_vip_customer_remains_eligible_for_portal(client, portal_context):
    user, customer = portal_context
    customer.status = Customer.Status.VIP
    customer.save(update_fields=["status", "updated_at"])
    client.force_login(user)

    assert client.get(reverse("portal:dashboard")).status_code == 200


@pytest.mark.django_db
def test_expired_client_role_revokes_portal_access(client, portal_context):
    user, _ = portal_context
    assignment = user.user_roles.get(role__code="cliente")
    assignment.expires_at = timezone.now() - timedelta(seconds=1)
    assignment.save(update_fields=["expires_at", "updated_at"])
    client.force_login(user)

    assert client.get(reverse("portal:dashboard")).status_code == 403


@pytest.mark.django_db
@pytest.mark.parametrize(
    "route_name",
    (
        "portal:profile",
        "portal:settings",
        "portal:vehicle_redeem",
        "portal:notification_read_all",
        "accounts:avatar_update",
        "accounts:avatar_delete",
    ),
)
def test_portal_mutations_require_csrf(portal_context, route_name):
    user, _ = portal_context
    csrf_client = Client(enforce_csrf_checks=True)
    csrf_client.force_login(user)

    response = csrf_client.post(reverse(route_name), {})

    assert response.status_code == 403


@pytest.mark.django_db
def test_client_login_lands_on_portal_dashboard(client, portal_context):
    user, _ = portal_context
    response = client.post(
        reverse("accounts:login"),
        {"username": user.email, "password": "VinovaCliente2026!"},
    )
    assert response.status_code == 302
    assert response.url == reverse("portal:dashboard")


@pytest.mark.django_db
def test_dashboard_only_lists_active_vehicles_owned_by_customer(client, portal_context):
    user, customer = portal_context
    other_user = type(user).objects.create_user(username="other-client", email="other-client@example.com", password="x")
    other_customer = Customer.objects.create(first_name="Otro", email=other_user.email, account=other_user)
    company = Company.objects.create(
        legal_name="Portal Vehicles S.A.", commercial_name="Portal Vehicles", ruc="1790000000088"
    )
    branch = Branch.objects.create(company=company, name="Matriz", code="POR-01")
    brand = VehicleBrand.objects.create(name="Portal Brand")
    model = VehicleModel.objects.create(brand=brand, name="Portal Model")
    own = Vehicle.objects.create(brand=brand, model=model, year=2025, branch=branch, public_slug="own-portal")
    foreign = Vehicle.objects.create(brand=brand, model=model, year=2024, branch=branch, public_slug="foreign-portal")
    inactive = Vehicle.objects.create(brand=brand, model=model, year=2023, branch=branch, public_slug="inactive-portal")
    CustomerVehicle.objects.create(customer=customer, vehicle=own)
    CustomerVehicle.objects.create(customer=other_customer, vehicle=foreign)
    CustomerVehicle.objects.create(customer=customer, vehicle=inactive, is_active=False)
    client.force_login(user)

    response = client.get(reverse("portal:dashboard"))
    content = response.content.decode()

    assert response.status_code == 200
    assert response.context["vehicle_count"] == 1
    assert "own-portal" not in content  # el slug interno no se expone
    assert "2025" in content
    assert "2024" not in content
    assert "2023" not in content


@pytest.mark.django_db
def test_profile_updates_only_allowed_contact_fields(client, portal_context):
    user, customer = portal_context
    client.force_login(user)
    response = client.post(
        reverse("portal:profile"),
        {
            "phone": "0981112233",
            "whatsapp": "0981112233",
            "address": "Av. Principal 123",
            "city": "Quito",
            "province": "Pichincha",
            "preferred_contact_method": Customer.ContactMethod.WHATSAPP,
            "identification_number": "9999999999",
            "first_name": "Alterada",
            "email": "attacker@example.com",
        },
    )
    assert response.status_code == 302
    customer.refresh_from_db()
    assert customer.phone == "0981112233"
    assert customer.city == "Quito"
    assert customer.identification_number == "0911453215"
    assert customer.first_name == "Ana"
    assert customer.email == user.email


@pytest.mark.django_db
def test_portal_dashboard_query_count_is_bounded(client, portal_context, django_assert_max_num_queries):
    user, _ = portal_context
    client.force_login(user)
    # Incluye bootstrap en frío de la política/sesión de seguridad en PostgreSQL.
    with django_assert_max_num_queries(32):
        response = client.get(reverse("portal:dashboard"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_dashboard_activity_and_breadcrumbs_are_private_and_accessible(client, portal_context):
    user, customer = portal_context
    own = NotificationMessage.objects.create(
        title="Actividad propia",
        body="Visible solo para su cuenta",
        message_type=NotificationMessage.MessageType.SYSTEM,
        dedup_key="dashboard-activity-own",
    )
    NotificationRecipient.objects.create(
        notification=own,
        recipient_type=NotificationRecipient.RecipientType.CUSTOMER,
        customer=customer,
    )
    foreign_customer = Customer.objects.create(first_name="Actividad ajena")
    foreign = NotificationMessage.objects.create(
        title="Actividad ajena",
        body="No visible",
        dedup_key="dashboard-activity-foreign",
    )
    NotificationRecipient.objects.create(
        notification=foreign,
        recipient_type=NotificationRecipient.RecipientType.CUSTOMER,
        customer=foreign_customer,
    )
    client.force_login(user)

    dashboard = client.get(reverse("portal:dashboard"))
    profile = client.get(reverse("portal:profile"))

    assert dashboard.status_code == 200
    assert "Actividad reciente" in dashboard.content.decode()
    assert "Actividad propia" in dashboard.content.decode()
    assert "Actividad ajena" not in dashboard.content.decode()
    profile_html = profile.content.decode()
    assert 'aria-label="Migas de pan"' in profile_html
    assert '<span aria-current="page">' in profile_html
    assert "Perfil" in profile_html


@pytest.mark.django_db
@override_settings(VINOVA_MODULE_POST_SALES_ENABLED=True)
def test_portal_shell_preserves_lite_navigation_and_progressive_vehicle_modal(client, portal_context):
    user, customer = portal_context
    brand = VehicleBrand.objects.create(name="Modal Brand")
    model = VehicleModel.objects.create(brand=brand, name="Modal Model")
    vehicle = Vehicle.objects.create(brand=brand, model=model, year=2026, public_slug="modal-vehicle")
    link = CustomerVehicle.objects.create(customer=customer, vehicle=vehicle)
    client.force_login(user)

    dashboard = client.get(reverse("portal:dashboard"))
    detail = client.get(reverse("portal:vehicle_detail", kwargs={"pk": link.pk}))
    dashboard_html = dashboard.content.decode()
    detail_html = detail.content.decode()

    assert 'class="portal-sidebar"' in dashboard_html
    for label in (
        "Inicio",
        "Mis vehículos",
        "Agregar vehículo",
        "Manuales",
        "Facturas",
        "Perfil",
        "Notificaciones",
        "Configuración",
    ):
        assert label in dashboard_html
    assert "data-portal-modal" in dashboard_html
    for label in ("Resumen", "Historial", "Mantenimiento", "Documentación"):
        assert label in detail_html
    assert detail_html.count('role="tabpanel"') == 4


@pytest.mark.django_db
def test_portal_brand_returns_to_public_hub_and_notification_uses_accessible_bell(client, portal_context):
    user, _ = portal_context
    client.force_login(user)

    response = client.get(reverse("portal:dashboard"))
    body = response.content.decode()

    assert response.status_code == 200
    assert f'href="{reverse("dashboard:home")}" aria-label="Ir al inicio público de Vinova Pro"' in body
    assert 'class="portal-bell' in body
    assert 'aria-label="Notificaciones' in body
    assert 'class="portal-notification-icon"' in body
    assert "♢" not in body


@pytest.mark.django_db
def test_legacy_profile_title_contains_no_markup(client, django_user_model):
    user = django_user_model.objects.create_user(username="profile-user", email="profile@example.com", password="x")
    get_security_profile(user)
    client.force_login(user)
    response = client.get(reverse("accounts:profile"))
    content = response.content.decode()
    title = content.split("<title>", 1)[1].split("</title>", 1)[0]
    assert response.status_code == 200
    assert title.strip() == "Mi perfil | Vinova Pro"
    assert "<section" not in title


@pytest.mark.django_db
def test_private_garage_list_and_search_only_show_active_owned_links(client, portal_context):
    user, customer = portal_context
    brand_a = VehicleBrand.objects.create(name="Toyota Portal")
    brand_b = VehicleBrand.objects.create(name="Honda Portal")
    model_a = VehicleModel.objects.create(brand=brand_a, name="Corolla")
    model_b = VehicleModel.objects.create(brand=brand_b, name="Civic")
    visible = Vehicle.objects.create(
        brand=brand_a, model=model_a, year=2025, plate="PBA1234", public_slug="portal-visible"
    )
    inactive = Vehicle.objects.create(
        brand=brand_b, model=model_b, year=2024, plate="PBB1234", public_slug="portal-inactive"
    )
    CustomerVehicle.objects.create(customer=customer, vehicle=visible)
    CustomerVehicle.objects.create(customer=customer, vehicle=inactive, is_active=False)
    client.force_login(user)

    response = client.get(reverse("portal:vehicle_list"), {"q": "Toyota"})
    content = response.content.decode()

    assert response.status_code == 200
    assert "Corolla" in content
    assert "Civic" not in content


@pytest.mark.django_db
def test_private_vehicle_detail_hides_foreign_inactive_and_non_public_media(client, portal_context):
    user, customer = portal_context
    brand = VehicleBrand.objects.create(name="Detalle Portal")
    model = VehicleModel.objects.create(brand=brand, name="Seguro")
    vehicle = Vehicle.objects.create(
        brand=brand,
        model=model,
        year=2026,
        vin="1HGCM82633A123456",
        public_slug="detalle-seguro",
    )
    link = CustomerVehicle.objects.create(customer=customer, vehicle=vehicle)
    public_resource = VehicleResource.objects.create(
        title="Foto autorizada", resource_type=VehicleResource.ResourceType.IMAGE, file="vehicles/resources/public.jpg"
    )
    private_resource = VehicleResource.objects.create(
        title="Foto interna secreta",
        resource_type=VehicleResource.ResourceType.IMAGE,
        file="vehicles/resources/private.jpg",
    )
    VehicleMedia.objects.create(
        vehicle=vehicle,
        resource=public_resource,
        media_type=VehicleMedia.MediaType.IMAGE,
        title="Vista autorizada",
        is_public=True,
    )
    VehicleMedia.objects.create(
        vehicle=vehicle,
        resource=private_resource,
        media_type=VehicleMedia.MediaType.IMAGE,
        title="Vista interna secreta",
        is_public=False,
    )
    client.force_login(user)

    response = client.get(reverse("portal:vehicle_detail", kwargs={"pk": link.pk}))
    content = response.content.decode()

    assert response.status_code == 200
    assert "Vista autorizada" in content
    assert "Vista interna secreta" not in content
    assert "1HGCM82633A123456" not in content
    assert "••••••123456" in content

    link.is_active = False
    link.save(update_fields=["is_active"])
    assert client.get(reverse("portal:vehicle_detail", kwargs={"pk": link.pk})).status_code == 404


@pytest.mark.django_db
def test_customer_cannot_open_another_customers_vehicle(client, portal_context, django_user_model):
    user, _ = portal_context
    other = Customer.objects.create(first_name="Ajeno", email="ajeno@example.com")
    brand = VehicleBrand.objects.create(name="Aislamiento Portal")
    model = VehicleModel.objects.create(brand=brand, name="Privado")
    vehicle = Vehicle.objects.create(brand=brand, model=model, year=2025, public_slug="vehiculo-ajeno")
    foreign_link = CustomerVehicle.objects.create(customer=other, vehicle=vehicle)
    client.force_login(user)
    assert client.get(reverse("portal:vehicle_detail", kwargs={"pk": foreign_link.pk})).status_code == 404


@pytest.mark.django_db
def test_portal_redeem_uses_existing_atomic_service(
    client,
    portal_context,
    django_capture_on_commit_callbacks,
):
    user, customer = portal_context
    brand = VehicleBrand.objects.create(name="Canje Portal")
    model = VehicleModel.objects.create(brand=brand, name="VNV")
    vehicle = Vehicle.objects.create(brand=brand, model=model, year=2026, public_slug="canje-portal")
    code = generate_vehicle_link_code(actor=None, vehicle=vehicle)
    client.force_login(user)

    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(
            reverse("portal:vehicle_redeem"),
            {"code": code.code, "mileage": 1200},
        )

    link = CustomerVehicle.objects.get(customer=customer, vehicle=vehicle, is_active=True)
    assert link.initial_mileage is None
    assert response.status_code == 302
    assert response.url == reverse("portal:vehicle_detail", kwargs={"pk": link.pk})
    code.refresh_from_db()
    assert code.status == VehicleLinkCode.Status.USED
    notification = NotificationMessage.objects.get(dedup_key=f"vehicle-link:{link.pk}:redeemed")
    assert notification.related_vehicle_id == vehicle.pk


@pytest.mark.django_db
def test_portal_redeem_invalid_code_stays_on_form(client, portal_context):
    user, _ = portal_context
    client.force_login(user)
    response = client.post(reverse("portal:vehicle_redeem"), {"code": "VNV-NO-VALIDO"})
    assert response.status_code == 200
    assert response.context["form"].errors["code"]
