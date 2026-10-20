"""ES: Este módulo especifica regresiones ejecutables para el dominio de portal cliente.

EN: This module specifies executable regressions for the portal domain.

Contexto existente / Existing context:
Regression coverage for services in the portal domain.
"""

from datetime import date

import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings
from django.urls import reverse

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer
from apps.notifications.models import NotificationMessage
from apps.portal.selectors import portal_service_orders_queryset
from apps.post_sales.forms import ServiceOrderOperationalForm
from apps.post_sales.models import ServiceOrder, ServiceOrderLine
from apps.post_sales.services import transition_service_order
from apps.vehicles.models import CustomerVehicle, Vehicle, VehicleBrand, VehicleModel


@pytest.fixture
def service_portal_context(db, django_user_model):
    portal_permission, _ = PermissionCode.objects.update_or_create(
        code="portal.access", defaults={"module": "portal", "name": "Acceso al portal"}
    )
    client_role, _ = Role.objects.update_or_create(
        code="cliente", defaults={"name": "Cliente", "level": 100, "is_active": True}
    )
    client_role.permissions.add(portal_permission)
    company = Company.objects.create(
        legal_name="Servicios Portal S.A.", commercial_name="Servicios Portal", ruc="1790000000077"
    )
    branch = Branch.objects.create(company=company, name="Taller Portal", code="SER-01")
    user = django_user_model.objects.create_user(
        username="service-client", email="service-client@example.com", password="x"
    )
    UserRole.objects.create(user=user, role=client_role)
    customer = Customer.objects.create(
        first_name="Cliente",
        last_name="Servicio",
        email=user.email,
        assigned_branch=branch,
        account=user,
        status=Customer.Status.ACTIVE,
    )
    brand = VehicleBrand.objects.create(name="Servicio Brand")
    model = VehicleModel.objects.create(brand=brand, name="Servicio Model")
    vehicle = Vehicle.objects.create(brand=brand, model=model, branch=branch, year=2026, public_slug="servicio-portal")
    link = CustomerVehicle.objects.create(customer=customer, vehicle=vehicle)
    return user, customer, branch, vehicle, link


@pytest.mark.django_db
def test_post_sales_module_off_hides_navigation_and_blocks_direct_url(client, service_portal_context):
    user, _, _, _, link = service_portal_context
    client.force_login(user)
    dashboard = client.get(reverse("portal:dashboard"))
    assert dashboard.status_code == 200
    assert reverse("portal:service_list") not in dashboard.content.decode()
    assert client.get(reverse("portal:service_list")).status_code == 404
    vehicle_detail = client.get(reverse("portal:vehicle_detail", kwargs={"pk": link.pk})).content.decode()
    assert "vehicle-tab-history" not in vehicle_detail
    assert "vehicle-tab-maintenance" not in vehicle_detail


@pytest.mark.django_db
@override_settings(VINOVA_MODULE_POST_SALES_ENABLED=True)
def test_portal_services_show_only_non_draft_orders_for_active_owned_vehicle(client, service_portal_context):
    user, customer, branch, vehicle, _ = service_portal_context
    visible = ServiceOrder.objects.create(
        number="PORTAL-SERVICE-1",
        branch=branch,
        customer=customer,
        vehicle=vehicle,
        status=ServiceOrder.Status.COMPLETED,
        description="Mantenimiento visible",
        diagnosis="Filtro reemplazado",
        reception_mileage=10000,
        delivery_mileage=10020,
        next_service_date=date(2027, 1, 15),
        next_service_mileage=15000,
    )
    ServiceOrderLine.objects.create(
        order=visible,
        line_type=ServiceOrderLine.LineType.SERVICE,
        description="Cambio de aceite",
    )
    ServiceOrder.objects.create(
        number="PORTAL-DRAFT",
        branch=branch,
        customer=customer,
        vehicle=vehicle,
        status=ServiceOrder.Status.DRAFT,
        description="Borrador interno",
    )
    client.force_login(user)

    response = client.get(reverse("portal:service_list"))
    content = response.content.decode()

    assert response.status_code == 200
    assert "PORTAL-SERVICE-1" in content
    assert "PORTAL-DRAFT" not in content
    detail = client.get(reverse("portal:service_detail", kwargs={"pk": visible.pk}))
    detail_content = detail.content.decode()
    assert detail.status_code == 200
    assert "Filtro reemplazado" in detail_content
    assert "15/01/2027" in detail_content
    assert "Cambio de aceite" in detail_content
    assert "no generan recordatorios automáticos" in detail_content
    filtered = client.get(
        reverse("portal:service_list"),
        {"q": "Mantenimiento visible", "status": ServiceOrder.Status.COMPLETED},
    ).content.decode()
    assert "PORTAL-SERVICE-1" in filtered
    assert "PORTAL-DRAFT" not in filtered


@pytest.mark.django_db
@override_settings(VINOVA_MODULE_POST_SALES_ENABLED=True)
def test_lite_equivalent_history_and_upcoming_views_are_separated(client, service_portal_context):
    user, customer, branch, vehicle, _ = service_portal_context
    ServiceOrder.objects.create(
        number="PORTAL-HISTORY",
        branch=branch,
        customer=customer,
        vehicle=vehicle,
        status=ServiceOrder.Status.COMPLETED,
        description="Servicio terminado",
    )
    ServiceOrder.objects.create(
        number="PORTAL-UPCOMING",
        branch=branch,
        customer=customer,
        vehicle=vehicle,
        status=ServiceOrder.Status.SCHEDULED,
        description="Servicio programado",
    )
    client.force_login(user)

    history = client.get(reverse("portal:service_list"), {"view": "history"})
    upcoming = client.get(reverse("portal:service_list"), {"view": "upcoming"})

    assert "PORTAL-HISTORY" in history.content.decode()
    assert "PORTAL-UPCOMING" not in history.content.decode()
    assert "PORTAL-UPCOMING" in upcoming.content.decode()
    assert "PORTAL-HISTORY" not in upcoming.content.decode()
    assert history.context["service_view"] == "history"
    assert upcoming.context["service_view"] == "upcoming"


@pytest.mark.django_db
@override_settings(VINOVA_MODULE_POST_SALES_ENABLED=True)
def test_portal_services_are_paginated_and_keep_filters(client, service_portal_context):
    user, customer, branch, vehicle, _ = service_portal_context
    for index in range(13):
        ServiceOrder.objects.create(
            number=f"PORTAL-PAGE-{index:02d}",
            branch=branch,
            customer=customer,
            vehicle=vehicle,
            status=ServiceOrder.Status.COMPLETED,
            description="Servicio paginado",
        )
    client.force_login(user)

    response = client.get(
        reverse("portal:service_list"),
        {"q": "paginado", "status": ServiceOrder.Status.COMPLETED},
    )

    assert response.status_code == 200
    assert len(response.context["orders"]) == 12
    assert response.context["page_obj"].paginator.num_pages == 2
    assert "q=paginado&amp;status=completed&amp;page=2" in response.content.decode()


@pytest.mark.django_db
@override_settings(VINOVA_MODULE_POST_SALES_ENABLED=True)
def test_transfer_cuts_former_access_and_does_not_expose_previous_customer_history(
    client, service_portal_context, django_user_model
):
    user, customer, branch, vehicle, link = service_portal_context
    order = ServiceOrder.objects.create(
        number="PORTAL-TRANSFERRED",
        branch=branch,
        customer=customer,
        vehicle=vehicle,
        status=ServiceOrder.Status.COMPLETED,
        description="Historial personal anterior",
    )
    link.is_active = False
    link.save(update_fields=["is_active"])
    client.force_login(user)
    assert client.get(reverse("portal:service_detail", kwargs={"pk": order.pk})).status_code == 404
    assert not portal_service_orders_queryset(customer).exists()


@pytest.mark.django_db
@override_settings(VINOVA_MODULE_POST_SALES_ENABLED=True)
def test_operational_details_validate_mileage_and_cancellation_reason(
    client,
    service_portal_context,
    django_user_model,
    django_capture_on_commit_callbacks,
):
    _, customer, branch, vehicle, _ = service_portal_context
    manage = PermissionCode.objects.create(module="post_sales", code="post_sales.manage", name="Gestionar postventa")
    role = Role.objects.create(code="service-manager", name="Service manager")
    role.permissions.add(manage)
    actor = django_user_model.objects.create_user(
        username="service-manager", email="service-manager@example.com", password="x"
    )
    UserRole.objects.create(user=actor, role=role, branch=branch)
    order = ServiceOrder.objects.create(
        number="PORTAL-OPERATIONAL",
        branch=branch,
        customer=customer,
        vehicle=vehicle,
        description="Diagnóstico",
    )
    invalid = ServiceOrderOperationalForm(
        {
            "reception_mileage": 20000,
            "delivery_mileage": 19999,
            "diagnosis": "No válido",
            "next_service_mileage": 25000,
        },
        instance=order,
    )
    assert not invalid.is_valid()
    assert "delivery_mileage" in invalid.errors

    valid = ServiceOrderOperationalForm(
        {
            "reception_mileage": 20000,
            "delivery_mileage": 20010,
            "diagnosis": "Sistema revisado",
            "next_service_date": "2027-02-01",
            "next_service_mileage": 25000,
        },
        instance=order,
    )
    assert valid.is_valid(), valid.errors
    client.force_login(actor)
    response = client.post(
        reverse("post_sales:operational_update", kwargs={"pk": order.pk}),
        {
            "reception_mileage": 20000,
            "delivery_mileage": 20010,
            "diagnosis": "Sistema revisado",
            "next_service_date": "2027-02-01",
            "next_service_mileage": 25000,
        },
    )
    assert response.status_code == 302
    order.refresh_from_db()
    assert order.delivery_mileage == 20010
    assert order.next_service_mileage == 25000

    with pytest.raises(ValidationError, match="motivo"):
        transition_service_order(
            actor=actor,
            order_id=order.pk,
            new_status=ServiceOrder.Status.CANCELLED,
        )
    with django_capture_on_commit_callbacks(execute=True):
        transition_service_order(
            actor=actor,
            order_id=order.pk,
            new_status=ServiceOrder.Status.CANCELLED,
            note="Cliente reprogramará",
        )
    order.refresh_from_db()
    assert order.cancellation_reason == "Cliente reprogramará"
    assert order.cancelled_at is not None
    notification = NotificationMessage.objects.get(
        dedup_key=f"service-order:{order.pk}:status:{ServiceOrder.Status.CANCELLED}"
    )
    assert notification.related_customer_id == customer.pk
    assert notification.related_vehicle_id == vehicle.pk
