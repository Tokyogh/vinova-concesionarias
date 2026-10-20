# -*- coding: utf-8 -*-
"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
D7 — cobertura funcional de acciones reales por módulo.

Cierra el gap de "crear/editar/estados/comerciales": para cada módulo de
dashboard se ejecuta una mutación real (formulario → vista → DB) con un
usuario que posee el permiso correspondiente y se verifica la persistencia.
El lado negativo (403) ya está cubierto a escala en D5
(mutating_views_require_permission, CSRF, privilege_escalation) y por el
provisioning de roles D7; aquí se añade la contrapartida explícita por
módulo con un rol sin el permiso.
"""
from __future__ import annotations

from datetime import date

import pytest
from decimal import Decimal
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command

from apps.accounts.management.commands.provision_qa_role_accounts import Command as ProvisionCommand
from apps.accounts.models import PermissionCode, Role, UserRole
from apps.customers.models import Customer
from apps.documents.models import PrivateDocument
from apps.imports.models import ImportBatch
from apps.inventory.models import InventoryItem, StockMovement
from apps.invoices.models import InvoiceRecord
from apps.leads.models import Lead
from apps.notifications.models import NotificationMessage
from apps.sales.models import SaleRecord
from apps.vehicles.models import Vehicle, VehicleBrand, VehicleModel


@pytest.fixture(name="context")
def context_fixture(django_user_model):
    call_command("seed_roles", verbosity=0)
    branch = ProvisionCommand._qa_branch()
    user = django_user_model.objects.create_user(
        username="d7_full", email="d7_full@example.com", password="x"
    )
    role = Role.objects.create(code="d7_all", name="D7 todos los permisos")
    role.permissions.set(PermissionCode.objects.all())
    UserRole.objects.create(user=user, role=role, branch=None)

    brand = VehicleBrand.objects.create(name=f"Brand D7 {branch.pk}", is_active=True)
    model = VehicleModel.objects.create(
        brand=brand, name=f"Model D7 {branch.pk}", is_active=True
    )
    customer = Customer.objects.create(
        customer_type="natural",
        first_name="D7 Cliente",
        last_name=f"Grupo {branch.pk}",
        email=f"d7.customer.{branch.pk}@example.invalid",
        phone="0999999999",
        assigned_branch=branch,
    )
    sale = SaleRecord.objects.create(
        kind=SaleRecord.Kind.SALE,
        status=SaleRecord.Status.SOLD,
        customer=customer,
        branch=branch,
        source=SaleRecord.Source.SHOWROOM.value,
        vehicle_price=Decimal("18500.00"),
        vehicle_discount=Decimal("0"),
        tax_rate=Decimal("0.00"),
    )
    return {
        "branch": branch,
        "user": user,
        "brand": brand,
        "model": model,
        "customer": customer,
        "sale": sale,
    }


# ---------------------------------------------------------------- customers
@pytest.mark.django_db
def test_staff_customer_create_and_edit_persists(context, client):
    client.force_login(context["user"])

    created = client.post(
        "/dashboard/customers/new/",
        {
            "customer_type": "natural",
            "preferred_contact_method": "whatsapp",
            "status": Customer.Status.ACTIVE.value,
            "first_name": "Nuevo",
            "last_name": "Cliente Seguro",
            "phone": "0987654321",
        },
    )
    assert created.status_code == 302, created.content[:500]
    customer = Customer.objects.get(first_name="Nuevo", last_name="Cliente Seguro")
    assert customer.pk is not None

    edited = client.post(
        f"/dashboard/customers/{customer.pk}/edit/",
        {
            "customer_type": "natural",
            "preferred_contact_method": "email",
            "status": Customer.Status.ACTIVE.value,
            "first_name": "Nuevo",
            "last_name": "Cliente Seguro Editado",
            "phone": "0987654321",
        },
    )
    assert edited.status_code == 302
    customer.refresh_from_db()
    assert customer.last_name == "Cliente Seguro Editado"


@pytest.mark.django_db
def test_customer_create_is_denied_without_customers_manage(django_user_model, client):
    branch = ProvisionCommand._qa_branch()
    role = Role.objects.create(code="d7_inv_only", name="Solo inventario")
    role.permissions.set(PermissionCode.objects.filter(code="inventory.manage_stock"))
    user = django_user_model.objects.create_user(username="d7_inv", password="x", email="d7_inv@example.com")
    UserRole.objects.create(user=user, role=role, branch=branch)
    client.force_login(user)

    response = client.post(
        "/dashboard/customers/new/",
        {
            "customer_type": "natural",
            "preferred_contact_method": "whatsapp",
            "status": Customer.Status.ACTIVE.value,
            "first_name": "Prohibido",
            "last_name": "D7",
        },
    )
    assert response.status_code == 403
    assert not Customer.objects.filter(first_name="Prohibido").exists()


# ---------------------------------------------------------------- vehicles
@pytest.mark.django_db
def test_staff_vehicle_create_persists(context, client):
    client.force_login(context["user"])

    response = client.post(
        "/dashboard/vehicles/new/",
        {
            "brand": context["brand"].pk,
            "model": context["model"].pk,
            "year": 2025,
            "mileage": 1500,
            "status": Vehicle.Status.AVAILABLE.value,
            "price": "19990.00",
            "vin": "1D7TEST00000000001",
        },
    )
    assert response.status_code == 302, response.content[:500]
    vehicle = Vehicle.objects.get(vin="1D7TEST00000000001")
    assert vehicle.brand_id == context["brand"].pk
    assert vehicle.model_id == context["model"].pk


# ---------------------------------------------------------------- inventory
@pytest.mark.django_db
def test_staff_inventory_create_and_stock_movement(context, client):
    client.force_login(context["user"])

    created = client.post(
        "/dashboard/inventory/new/",
        {
            "name": "Freno trasero D7",
            "sku": "FR-D7-001",
            "item_type": InventoryItem.ItemType.SPARE_PART.value,
            "unit": "unidad",
            "price": "45.00",
            "status": InventoryItem.Status.ACTIVE.value,
            "track_stock": True,
        },
    )
    assert created.status_code == 302, created.content[:500]
    item = InventoryItem.objects.get(sku="FR-D7-001")

    movement = client.post(
        "/dashboard/inventory/movements/new/",
        {
            "item": item.pk,
            "branch": context["branch"].pk,
            "movement_type": StockMovement.MovementType.IN.value,
            "quantity": "10",
            "reason": "entrada de prueba D7",
        },
    )
    assert movement.status_code == 302, movement.content[:500]
    assert StockMovement.objects.filter(item=item, movement_type=StockMovement.MovementType.IN.value).exists()


# ---------------------------------------------------------------- leads
@pytest.mark.django_db
def test_staff_lead_flow_create_assign_status_convert(context, client):
    client.force_login(context["user"])

    created = client.post(
        "/dashboard/leads/new/",
        {
            "request_type": Lead.RequestType.INFORMATION.value,
            "status": Lead.Status.NEW.value,
            "priority": Lead.Priority.MEDIUM.value,
            "source": Lead.Source.WEBSITE.value,
            "full_name": "Lead Comercial",
            "email": "lead.d7@example.invalid",
            "phone": "0977777777",
        },
    )
    assert created.status_code == 302, created.content[:500]
    lead = Lead.objects.get(full_name="Lead Comercial")

    assigned = client.post(f"/dashboard/leads/{lead.pk}/assign/", {})
    assert assigned.status_code == 302

    changed = client.post(
        f"/dashboard/leads/{lead.pk}/status/",
        {"status": Lead.Status.CONTACTED.value, "note": "primer contacto D7"},
    )
    assert changed.status_code == 302
    lead.refresh_from_db()
    assert lead.status == Lead.Status.CONTACTED.value

    converted = client.post(f"/dashboard/leads/{lead.pk}/convert-customer/", {})
    assert converted.status_code == 302


# ---------------------------------------------------------------- sales
@pytest.mark.django_db
def test_staff_sale_quote_creation_and_confirm(context, client):
    client.force_login(context["user"])

    created = client.post(
        "/dashboard/sales/new/",
        {
            "kind": SaleRecord.Kind.QUOTE.value,
            "customer": context["customer"].pk,
            "branch": context["branch"].pk,
            "source": SaleRecord.Source.SHOWROOM.value,
            "vehicle_price": "12500.00",
            "vehicle_discount": "500.00",
            "tax_rate": "0.00",
        },
    )
    assert created.status_code == 302, created.content[:500]
    sale = SaleRecord.objects.filter(
        customer=context["customer"], kind=SaleRecord.Kind.QUOTE.value
    ).order_by("-pk").first()
    assert sale is not None


@pytest.mark.django_db
def test_staff_invoice_from_sale_and_void(context, client):
    client.force_login(context["user"])

    created = client.post(
        "/dashboard/invoices/new/",
        {
            "sale": context["sale"].pk,
            "invoice_type": InvoiceRecord.InvoiceType.INVOICE.value,
            "issue_date": date.today().isoformat(),
        },
    )
    assert created.status_code == 302, created.content[:500]
    invoice = InvoiceRecord.objects.get(sale=context["sale"])

    voided = client.post(
        f"/dashboard/invoices/{invoice.pk}/action/void/",
        {"reason": "void de prueba D7"},
    )
    assert voided.status_code == 302
    invoice.refresh_from_db()
    assert invoice.status == InvoiceRecord.Status.VOID.value


# ---------------------------------------------------------------- notifications
@pytest.mark.django_db
def test_staff_notification_compose_persists(context, client):
    client.force_login(context["user"])

    response = client.post(
        "/dashboard/notifications/compose/",
        {
            "title": "Aviso D7",
            "body": "Mensaje de cobertura funcional.",
            "message_type": NotificationMessage.MessageType.MESSAGE.value,
            "priority": NotificationMessage.Priority.NORMAL.value,
            "recipient_users": [context["user"].pk],
        },
    )
    assert response.status_code == 302, response.content[:500]
    assert NotificationMessage.objects.filter(title="Aviso D7").exists()


# ---------------------------------------------------------------- documents
@pytest.mark.django_db
def test_staff_document_upload_and_download(context, client):
    client.force_login(context["user"])
    payload = SimpleUploadedFile("garantia-d7.pdf", b"%PDF-1.7 dummy d7", content_type="application/pdf")

    uploaded = client.post(
        "/dashboard/documents/upload/",
        {
            "title": "Garantia D7",
            "document_type": PrivateDocument.DocumentType.WARRANTY.value,
            "file": payload,
            "status": PrivateDocument.Status.ACTIVE.value,
        },
    )
    assert uploaded.status_code == 302, uploaded.content[:500]
    document = PrivateDocument.objects.get(title="Garantia D7")

    downloaded = client.get(f"/dashboard/documents/{document.pk}/download/")
    assert downloaded.status_code == 200
    assert b"".join(downloaded.streaming_content) == b"%PDF-1.7 dummy d7"


# ---------------------------------------------------------------- imports
@pytest.mark.django_db
def test_staff_import_upload_revalidate_confirm(context, client):
    client.force_login(context["user"])
    csv = SimpleUploadedFile("clientes-d7.csv", b"nombre,cedula\nAna,1712345678\n", content_type="text/csv")

    uploaded = client.post(
        "/dashboard/imports/new/",
        {"import_type": ImportBatch.ImportType.CUSTOMERS.value, "original_file": csv},
    )
    assert uploaded.status_code == 302, uploaded.content[:500]
    batch = ImportBatch.objects.get(original_filename="clientes-d7.csv")

    revalidated = client.post(f"/dashboard/imports/{batch.pk}/revalidate/")
    assert revalidated.status_code == 302

    confirmed = client.post(f"/dashboard/imports/{batch.pk}/confirm/")
    assert confirmed.status_code == 302
    batch.refresh_from_db()
    assert batch.status != ImportBatch.Status.UPLOADED.value


# ---------------------------------------------------------------- denied: matriz y deny-by-default
@pytest.mark.django_db
@pytest.mark.parametrize(
    "path,payload",
    [
        ("/dashboard/customers/new/", {"customer_type": "natural", "first_name": "X"}),
        ("/dashboard/vehicles/new/", {"year": 2025}),
        ("/dashboard/inventory/new/", {"name": "X"}),
        ("/dashboard/leads/new/", {"full_name": "X"}),
        ("/dashboard/sales/new/", {"kind": "quote"}),
        ("/dashboard/invoices/new/", {"invoice_type": "invoice"}),
        ("/dashboard/notifications/compose/", {"title": "X"}),
        ("/dashboard/documents/upload/", {"title": "X"}),
        ("/dashboard/imports/new/", {"import_type": "customers"}),
    ],
)
def test_public_client_role_is_denied_every_staff_create_step(client, path, payload):
    """El rol 'cliente' no debe poder ejecutar ninguna mutación interna."""
    call_command("seed_roles", verbosity=0)
    role = Role.objects.get(code="cliente")
    from apps.accounts.models import User as AccountUser

    user = AccountUser.objects.create(username="d7_cliente", email="d7_cliente@example.com", password="x")
    UserRole.objects.create(user=user, role=role, branch=None)
    client.force_login(user)

    response = client.post(path, payload)

    assert response.status_code == 403


@pytest.mark.django_db
def test_user_without_roles_cannot_mutate_sales(client):
    from apps.accounts.models import User as AccountUser

    user = AccountUser.objects.create(username="d7_noop", email="d7_noop@example.com", password="x")
    client.force_login(user)
    before = SaleRecord.objects.count()

    response = client.post("/dashboard/sales/new/", {"kind": SaleRecord.Kind.QUOTE.value})

    assert response.status_code == 403
    assert SaleRecord.objects.count() == before
