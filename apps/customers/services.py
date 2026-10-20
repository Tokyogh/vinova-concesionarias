"""ES: Este módulo implementa servicios de negocio y efectos transaccionales para el dominio de clientes.

EN: This module implements business services and transactional effects for the customers domain.

Contexto existente / Existing context:
Transactional business services for the customers domain.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.scopes import accessible_branch_ids
from apps.audit.services import audit_log
from apps.customers.models import Customer, CustomerNote, CustomerVehicleInterest


def _customer_snapshot(customer: Customer) -> dict:
    return {
        "customer_type": customer.customer_type,
        "identification_number": customer.identification_number,
        "display_name": customer.display_name,
        "email": customer.email,
        "phone": customer.phone,
        "whatsapp": customer.whatsapp,
        "status": customer.status,
        "assigned_branch": customer.assigned_branch_id,
        "assigned_advisor": customer.assigned_advisor_id,
    }


def _require_customer_branch_access(*, actor, customer: Customer) -> None:
    branch_ids = accessible_branch_ids(actor, permission_codes=("customers.manage",))
    if branch_ids is not None and (
        customer.assigned_branch_id is None or customer.assigned_branch_id not in branch_ids
    ):
        raise ValidationError("No tienes permiso para gestionar clientes en esta sucursal.")


def _audit_identification_change(*, actor, customer: Customer, before_value, after_value) -> None:
    if (before_value or "") == (after_value or ""):
        return
    audit_log(
        user=actor,
        action="customers.identification_change",
        target=customer,
        before={"identification_number": before_value},
        after={"identification_number": after_value},
        severity="medium",
        is_sensitive=True,
    )


def _validate_customer_assignment(*, actor, customer: Customer) -> None:
    _require_customer_branch_access(actor=actor, customer=customer)
    if customer.assigned_advisor_id and customer.assigned_branch_id:
        has_active_assignment = customer.assigned_advisor.active_role_assignments().filter(
            Q(branch_id=customer.assigned_branch_id) | Q(branch__isnull=True)
        ).exists()
        if not has_active_assignment:
            raise ValidationError("El asesor no tiene una asignación activa para esta sucursal.")


def _validate_interest_vehicle(interest: CustomerVehicleInterest) -> None:
    if (
        interest.vehicle_id
        and interest.customer.assigned_branch_id
        and interest.vehicle.branch_id not in (None, interest.customer.assigned_branch_id)
    ):
        raise ValidationError("El vehículo pertenece a otra sucursal.")


def _persist_new_customer(*, actor, customer: Customer) -> Customer:
    customer.created_by = actor if getattr(actor, "is_authenticated", False) else None
    _validate_customer_assignment(actor=actor, customer=customer)
    customer.full_clean()
    customer.save()
    audit_log(user=actor, action="customers.create", target=customer, after=_customer_snapshot(customer))
    return customer


@transaction.atomic
def create_customer(*, actor, form) -> Customer:
    customer = form.save(commit=False)
    customer = _persist_new_customer(actor=actor, customer=customer)
    form.save_m2m()
    return customer


@transaction.atomic
def create_customer_from_data(*, actor, validated_data: dict) -> Customer:
    return _persist_new_customer(actor=actor, customer=Customer(**validated_data))


@transaction.atomic
def update_customer(*, actor, customer: Customer, form) -> Customer:
    before = _customer_snapshot(customer)
    customer = form.save(commit=False)
    _validate_customer_assignment(actor=actor, customer=customer)
    customer.full_clean()
    customer.save()
    form.save_m2m()
    audit_log(user=actor, action="customers.update", target=customer, before=before, after=_customer_snapshot(customer))
    _audit_identification_change(
        actor=actor, customer=customer, before_value=before["identification_number"], after_value=customer.identification_number
    )
    return customer


@transaction.atomic
def update_customer_from_data(*, actor, customer: Customer, validated_data: dict) -> Customer:
    before = _customer_snapshot(customer)
    for field, value in validated_data.items():
        setattr(customer, field, value)
    _validate_customer_assignment(actor=actor, customer=customer)
    customer.full_clean()
    customer.save()
    audit_log(user=actor, action="customers.update", target=customer, before=before, after=_customer_snapshot(customer))
    _audit_identification_change(
        actor=actor, customer=customer, before_value=before["identification_number"], after_value=customer.identification_number
    )
    return customer


@transaction.atomic
def archive_customer(*, actor, customer: Customer) -> Customer:
    before = _customer_snapshot(customer)
    customer.status = Customer.Status.ARCHIVED
    customer.is_deleted = False
    customer.save(update_fields=["status", "is_deleted", "updated_at"])
    audit_log(user=actor, action="customers.archive", target=customer, before=before, after=_customer_snapshot(customer))
    return customer


@transaction.atomic
def activate_customer(*, actor, customer: Customer) -> Customer:
    before = _customer_snapshot(customer)
    customer.status = Customer.Status.ACTIVE
    customer.deleted_at = None
    customer.is_deleted = False
    customer.save(update_fields=["status", "deleted_at", "is_deleted", "updated_at"])
    audit_log(user=actor, action="customers.activate", target=customer, before=before, after=_customer_snapshot(customer))
    return customer


@transaction.atomic
def soft_delete_customer(*, actor, customer: Customer) -> Customer:
    before = _customer_snapshot(customer)
    customer.is_deleted = True
    customer.deleted_at = timezone.now()
    customer.status = Customer.Status.ARCHIVED
    customer.save(update_fields=["is_deleted", "deleted_at", "status", "updated_at"])
    audit_log(user=actor, action="customers.soft_delete", target=customer, before=before, after=_customer_snapshot(customer))
    return customer


@transaction.atomic
def add_customer_note(*, actor, customer: Customer, form) -> CustomerNote:
    _require_customer_branch_access(actor=actor, customer=customer)
    note = form.save(commit=False)
    note.customer = customer
    note.created_by = actor if getattr(actor, "is_authenticated", False) else None
    note.save()
    audit_log(user=actor, action="customers.note_create", target=customer, after={"note": note.title or note.note_type, "important": note.is_important})
    return note


@transaction.atomic
def add_customer_note_from_data(*, actor, validated_data: dict) -> CustomerNote:
    note = CustomerNote(**validated_data)
    _require_customer_branch_access(actor=actor, customer=note.customer)
    note.created_by = actor if getattr(actor, "is_authenticated", False) else None
    note.full_clean()
    note.save()
    audit_log(
        user=actor,
        action="customers.note_create",
        target=note.customer,
        after={"note": note.title or note.note_type, "important": note.is_important},
    )
    return note


@transaction.atomic
def link_customer_account(*, actor, customer: Customer, user) -> Customer:
    """Vincula una cuenta de acceso al expediente de cliente (portal/garaje)."""
    _require_customer_branch_access(actor=actor, customer=customer)
    if user is None or not getattr(user, "pk", None):
        raise ValidationError("Selecciona una cuenta de usuario.")
    user = type(user).objects.select_for_update().get(pk=user.pk)
    customer = Customer.objects.select_for_update().get(pk=customer.pk)
    if not user.is_active:
        raise ValidationError("La cuenta seleccionada está inactiva.")
    if not user.has_perm_code("portal.access"):
        raise ValidationError("La cuenta seleccionada no tiene el rol o permiso de acceso al portal.")
    existing = Customer.objects.filter(account=user).exclude(pk=customer.pk).first()
    if existing is not None:
        raise ValidationError("Esa cuenta ya está vinculada a otro expediente de cliente.")
    before = {"account": customer.account_id}
    customer.account = user
    customer.save(update_fields=["account", "updated_at"])
    audit_log(user=actor, action="customers.account_link", target=customer, before=before, after={"account": customer.account_id})
    return customer


@transaction.atomic
def add_vehicle_interest(*, actor, customer: Customer, form) -> CustomerVehicleInterest:
    _require_customer_branch_access(actor=actor, customer=customer)
    interest = form.save(commit=False)
    interest.customer = customer
    interest.created_by = actor if getattr(actor, "is_authenticated", False) else None
    _validate_interest_vehicle(interest)
    interest.save()
    audit_log(
        user=actor,
        action="customers.interest_create",
        target=customer,
        after={"vehicle": interest.vehicle_id, "brand": interest.brand, "model": interest.model_name, "status": interest.status},
    )
    return interest


@transaction.atomic
def add_vehicle_interest_from_data(*, actor, validated_data: dict) -> CustomerVehicleInterest:
    interest = CustomerVehicleInterest(**validated_data)
    _require_customer_branch_access(actor=actor, customer=interest.customer)
    _validate_interest_vehicle(interest)
    interest.created_by = actor if getattr(actor, "is_authenticated", False) else None
    interest.full_clean()
    interest.save()
    audit_log(
        user=actor,
        action="customers.interest_create",
        target=interest.customer,
        after={
            "vehicle": interest.vehicle_id,
            "brand": interest.brand,
            "model": interest.model_name,
            "status": interest.status,
        },
    )
    return interest
