"""ES: Este módulo especifica regresiones ejecutables para el dominio de vehículos.

EN: This module specifies executable regressions for the vehicles domain.

Contexto existente / Existing context:
Regression coverage for garage in the vehicles domain.
"""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, connections, transaction
from django.urls import reverse

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer
from apps.customers.services import link_customer_account
from apps.vehicles.models import CustomerVehicle, Vehicle, VehicleBrand, VehicleLinkCode, VehicleModel
from apps.vehicles.services import (
    generate_vehicle_link_code,
    redeem_link_code,
    revoke_vehicle_link_code,
    transfer_customer_vehicle,
    unlink_customer_vehicle,
)

User = get_user_model()


@pytest.fixture
def garage_permissions():
    perms = {}
    for code in ["vehicles.link_codes", "portal.access", "customers.manage", "vehicles.manage", "vehicles.view"]:
        module = code.split(".")[0]
        perms[code], _ = PermissionCode.objects.get_or_create(module=module, code=code, defaults={"name": code})
    return perms


@pytest.fixture
def garage_user(django_user_model, garage_permissions):
    user = django_user_model.objects.create_user(username="garageop", email="garageop@example.com", password="x")
    role = Role.objects.create(code="garage_op", name="Garage Operator")
    role.permissions.add(*garage_permissions.values())
    UserRole.objects.create(user=user, role=role)
    return user


@pytest.fixture
def garage_company():
    return Company.objects.create(legal_name="Garage S.A.", commercial_name="Garage", ruc="1790000000007")


@pytest.fixture
def garage_branch(garage_company):
    return Branch.objects.create(company=garage_company, name="Sucursal Garage", code="GRG-01", city="Quito")


@pytest.fixture
def customer_one(garage_branch):
    return Customer.objects.create(
        first_name="Ana",
        last_name="Perez",
        identification_number="1712345678",
        identification_type="cedula_ec",
        email="ana@example.com",
        status=Customer.Status.ACTIVE,
        assigned_branch=garage_branch,
    )


@pytest.fixture
def customer_two(garage_branch):
    return Customer.objects.create(
        first_name="Luis",
        last_name="Mora",
        identification_number="1798765432",
        identification_type="cedula_ec",
        email="luis@example.com",
        status=Customer.Status.ACTIVE,
        assigned_branch=garage_branch,
    )


@pytest.fixture
def garage_vehicle(garage_branch):
    brand, _ = VehicleBrand.objects.get_or_create(name="Toyota")
    model, _ = VehicleModel.objects.get_or_create(brand=brand, name="Corolla", defaults={"segment": "Sedan"})
    return Vehicle.objects.create(
        brand=brand,
        model=model,
        year=2023,
        public_slug="toyota-corolla",
        branch=garage_branch,
        mileage=15000,
    )


@pytest.mark.django_db
def test_generate_link_code_format_and_uniqueness(garage_user, garage_vehicle):
    code1 = generate_vehicle_link_code(actor=garage_user, vehicle=garage_vehicle)
    assert code1.code.startswith("VNV-")
    assert len(code1.code) == 23
    # generates second different code and revokes first
    code2 = generate_vehicle_link_code(actor=garage_user, vehicle=garage_vehicle)
    code1.refresh_from_db()
    assert code1.status == VehicleLinkCode.Status.REVOKED
    assert code2.status == VehicleLinkCode.Status.ACTIVE
    assert code2.code != code1.code


@pytest.mark.django_db
def test_link_code_expires_and_is_rejected(garage_user, garage_vehicle, customer_one):
    code = generate_vehicle_link_code(actor=garage_user, vehicle=garage_vehicle, expires_after_days=-1)
    code.refresh_from_db()
    assert code.is_expired
    with pytest.raises(ValidationError):
        redeem_link_code(customer=customer_one, code=code.code)


@pytest.mark.django_db
def test_revoke_link_code(garage_user, garage_vehicle):
    code = generate_vehicle_link_code(actor=garage_user, vehicle=garage_vehicle)
    revoked = revoke_vehicle_link_code(actor=garage_user, link_code=code, reason="test")
    assert revoked.status == VehicleLinkCode.Status.REVOKED


@pytest.mark.django_db
def test_redeem_link_code_creates_garage_link(garage_user, garage_vehicle, customer_one):
    code = generate_vehicle_link_code(actor=garage_user, vehicle=garage_vehicle)
    link = redeem_link_code(actor=garage_user, customer=customer_one, code=code.code)
    assert link.customer == customer_one
    assert link.vehicle == garage_vehicle
    assert link.initial_mileage == garage_vehicle.mileage
    assert link.is_active
    code.refresh_from_db()
    assert code.status == VehicleLinkCode.Status.USED
    assert code.used_by == customer_one


@pytest.mark.django_db
def test_double_redeem_is_rejected(garage_user, garage_vehicle, customer_one, customer_two):
    code = generate_vehicle_link_code(actor=garage_user, vehicle=garage_vehicle)
    redeem_link_code(customer=customer_one, code=code.code)
    with pytest.raises(ValidationError):
        redeem_link_code(customer=customer_two, code=code.code)


@pytest.mark.django_db
def test_unlink_preserves_history(garage_user, garage_vehicle, customer_one):
    code = generate_vehicle_link_code(actor=garage_user, vehicle=garage_vehicle)
    link = redeem_link_code(customer=customer_one, code=code.code)
    unlink_customer_vehicle(actor=garage_user, link=link, reason="venta")
    link.refresh_from_db()
    assert not link.is_active
    assert link.unlinked_reason
    assert link.unlinked_at is not None


@pytest.mark.django_db
def test_transfer_changes_owner_preserves_history(garage_user, garage_vehicle, customer_one, customer_two):
    code = generate_vehicle_link_code(actor=garage_user, vehicle=garage_vehicle)
    link = redeem_link_code(customer=customer_one, code=code.code)
    new_link = transfer_customer_vehicle(actor=garage_user, link=link, new_customer=customer_two, reason="venta")
    link.refresh_from_db()
    assert not link.is_active
    assert new_link.is_active
    assert new_link.customer == customer_two
    assert CustomerVehicle.objects.filter(vehicle=garage_vehicle).count() == 2


@pytest.mark.django_db
def test_redeem_endpoint_requires_login(client, garage_vehicle, customer_one):
    url = reverse("vehicles:redeem")
    resp = client.get(url)
    assert resp.status_code == 302


@pytest.mark.django_db
def test_redeem_endpoint_requires_portal_access(client, django_user_model, garage_vehicle, customer_one):
    url = reverse("vehicles:redeem")
    user = django_user_model.objects.create_user(username="noclient", email="noclient@example.com", password="x")
    client.force_login(user)
    resp = client.post(url, {"code": "BAD"})
    assert resp.status_code == 302  # redirects to catalog
    # no link created
    assert CustomerVehicle.objects.count() == 0


@pytest.mark.django_db
def test_redeem_get_requires_portal_access(client, django_user_model):
    user = django_user_model.objects.create_user(username="noportal", email="noportal@example.com", password="x")
    client.force_login(user)

    response = client.get(reverse("vehicles:redeem"))

    assert response.status_code == 302
    assert response.url == reverse("vehicles:catalog")


@pytest.mark.django_db
def test_database_rejects_two_active_owners(garage_vehicle, customer_one, customer_two):
    CustomerVehicle.objects.create(customer=customer_one, vehicle=garage_vehicle)

    with pytest.raises(IntegrityError), transaction.atomic():
        CustomerVehicle.objects.create(customer=customer_two, vehicle=garage_vehicle)


@pytest.mark.django_db(transaction=True)
def test_concurrent_redeem_creates_only_one_owner(
    garage_user, garage_vehicle, customer_one, customer_two
):
    if connection.vendor != "postgresql":
        pytest.skip("La carrera se valida con locks reales de PostgreSQL.")
    code = generate_vehicle_link_code(actor=garage_user, vehicle=garage_vehicle)
    barrier = Barrier(2)

    def redeem(customer_id):
        connections.close_all()
        try:
            customer = Customer.objects.get(pk=customer_id)
            barrier.wait()
            try:
                link = redeem_link_code(customer=customer, code=code.code)
            except ValidationError:
                return "rejected", None
            return "created", link.pk
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(redeem, [customer_one.pk, customer_two.pk]))

    assert sorted(status for status, _ in results) == ["created", "rejected"]
    assert CustomerVehicle.objects.filter(vehicle=garage_vehicle, is_active=True).count() == 1


@pytest.mark.django_db
def test_link_customer_account_requires_portal_permission(garage_user, django_user_model, customer_one):
    user = django_user_model.objects.create_user(username="withoutportal", email="withoutportal@example.com", password="x")

    with pytest.raises(ValidationError, match="acceso al portal"):
        link_customer_account(actor=garage_user, customer=customer_one, user=user)


@pytest.mark.django_db
def test_link_customer_account_accepts_active_portal_user(
    garage_user, django_user_model, garage_permissions, customer_one
):
    user = django_user_model.objects.create_user(username="portaluser", email="portaluser@example.com", password="x")
    role = Role.objects.create(code="client_link_test", name="Client link test")
    role.permissions.add(garage_permissions["portal.access"])
    UserRole.objects.create(user=user, role=role)

    linked = link_customer_account(actor=garage_user, customer=customer_one, user=user)

    assert linked.account == user


@pytest.mark.django_db
def test_redeem_endpoint_success(client, django_user_model, garage_permissions, garage_vehicle, customer_one):
    user = django_user_model.objects.create_user(username="clientuser", email="client@example.com", password="x")
    role = Role.objects.create(code="cliente_test", name="Cliente Test")
    role.permissions.add(garage_permissions["portal.access"])
    UserRole.objects.create(user=user, role=role)
    customer_one.account = user
    customer_one.save()
    code = generate_vehicle_link_code(actor=None, vehicle=garage_vehicle)
    client.force_login(user)
    resp = client.post(reverse("vehicles:redeem"), {"code": code.code})
    assert resp.status_code == 302
    assert CustomerVehicle.objects.filter(customer=customer_one, vehicle=garage_vehicle, is_active=True).exists()
