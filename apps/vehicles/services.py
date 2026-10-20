"""ES: Este módulo implementa servicios de negocio y efectos transaccionales para el dominio de vehículos.

EN: This module implements business services and transactional effects for the vehicles domain.

Contexto existente / Existing context:
Transactional business services for the vehicles domain.
"""

from __future__ import annotations

import re
from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.accounts.scopes import accessible_branch_ids
from apps.audit.services import audit_log
from apps.common.db_locks import acquire_transaction_advisory_lock
from apps.customers.models import Customer
from apps.vehicles.models import (
    CustomerVehicle,
    Vehicle,
    VehicleBrand,
    VehicleCommercialHighlight,
    VehicleLinkCode,
    VehicleMedia,
    VehicleModel,
    VehiclePartSpecification,
)

COMMERCIAL_VEHICLE_STATUSES = {Vehicle.Status.RESERVED, Vehicle.Status.SOLD}
PUBLISHING_VEHICLE_STATUSES = {Vehicle.Status.AVAILABLE, Vehicle.Status.HIDDEN, Vehicle.Status.ARCHIVED}


def _require_vehicle_permission(*, actor, code: str, branch) -> None:
    if actor is None:
        return
    if branch is None:
        if accessible_branch_ids(actor, permission_codes=(code,)) is not None:
            raise ValidationError("No tienes alcance global para gestionar vehículos sin sucursal.")
        return
    if not actor.has_perm_code(code, branch=branch):
        raise ValidationError("No tienes permiso para gestionar vehículos en esta sucursal.")


def _validate_status_change(*, actor, branch, previous: str, new: str) -> None:
    if previous == new:
        return
    if new in COMMERCIAL_VEHICLE_STATUSES or previous in COMMERCIAL_VEHICLE_STATUSES:
        raise ValidationError("Los estados reservado y vendido solo cambian desde el flujo comercial.")
    if not previous:
        if new == Vehicle.Status.AVAILABLE:
            _require_vehicle_permission(actor=actor, code="vehicles.publish", branch=branch)
        return
    if new in PUBLISHING_VEHICLE_STATUSES or previous == Vehicle.Status.AVAILABLE:
        _require_vehicle_permission(actor=actor, code="vehicles.publish", branch=branch)


def _apply_vehicle_data(vehicle: Vehicle, validated_data: dict) -> Vehicle:
    editable_fields = {
        "brand",
        "model",
        "branch",
        "year",
        "version",
        "vin",
        "plate",
        "color",
        "mileage",
        "price",
        "status",
        "short_description",
        "description",
        "is_featured",
    }
    for field, value in validated_data.items():
        if field in editable_fields:
            setattr(vehicle, field, value)
    if vehicle.brand_id and vehicle.model_id and vehicle.model.brand_id != vehicle.brand_id:
        raise ValidationError("El modelo seleccionado no pertenece a la marca indicada.")
    return vehicle


def _prepare_vehicle_identifiers(vehicle: Vehicle) -> None:
    acquire_transaction_advisory_lock(namespace="vehicle-identifiers", value="global")
    if not vehicle.internal_code:
        vehicle.internal_code = vehicle.generate_internal_code()
    vehicle.public_slug = _unique_vehicle_slug(vehicle)


def _locked_vehicle(vehicle: Vehicle) -> Vehicle:
    return Vehicle.objects.select_for_update().get(
        pk=vehicle.pk,
        is_deleted=False,
    )


def _unique_vehicle_slug(vehicle: Vehicle) -> str:
    base = slugify(f"{vehicle.year}-{vehicle.brand.name}-{vehicle.model.name}-{vehicle.version or vehicle.internal_code or vehicle.vin or 'vehiculo'}")[:150]
    base = base or f"vehiculo-{(vehicle.internal_code or vehicle.vin or 'nuevo').lower()}"
    candidate = base
    counter = 2
    qs = Vehicle.objects.all()
    if vehicle.pk:
        qs = qs.exclude(pk=vehicle.pk)
    while qs.filter(public_slug=candidate).exists():
        suffix = f"-{counter}"
        candidate = f"{base[:180-len(suffix)]}{suffix}"
        counter += 1
    return candidate


def _vehicle_snapshot(vehicle: Vehicle) -> dict:
    return {
        "brand": vehicle.brand_id,
        "model": vehicle.model_id,
        "branch": vehicle.branch_id,
        "year": vehicle.year,
        "version": vehicle.version,
        "internal_code": vehicle.internal_code,
        "vin": vehicle.vin,
        "plate": vehicle.plate,
        "color": vehicle.color,
        "mileage": vehicle.mileage,
        "status": vehicle.status,
        "price": str(vehicle.price) if vehicle.price is not None else None,
        "short_description": vehicle.short_description,
        "description": vehicle.description,
        "is_featured": vehicle.is_featured,
    }


@transaction.atomic
def create_vehicle(*, actor, form) -> Vehicle:
    vehicle = create_vehicle_from_data(actor=actor, validated_data=form.cleaned_data)
    form.instance = vehicle
    return vehicle


@transaction.atomic
def create_vehicle_from_data(*, actor, validated_data: dict) -> Vehicle:
    vehicle = _apply_vehicle_data(Vehicle(), validated_data)
    _require_vehicle_permission(actor=actor, code="vehicles.manage", branch=vehicle.branch)
    _validate_status_change(actor=actor, branch=vehicle.branch, previous="", new=vehicle.status)
    _prepare_vehicle_identifiers(vehicle)
    if vehicle.status == Vehicle.Status.AVAILABLE and not vehicle.published_at:
        vehicle.published_at = timezone.now()
    vehicle.full_clean()
    vehicle.save()
    audit_log(
        user=actor,
        action="vehicles.create",
        target=vehicle,
        branch=vehicle.branch,
        after=_vehicle_snapshot(vehicle),
    )
    return vehicle


@transaction.atomic
def update_vehicle(*, actor, vehicle: Vehicle, form) -> Vehicle:
    vehicle = update_vehicle_from_data(actor=actor, vehicle=vehicle, validated_data=form.cleaned_data)
    form.instance = vehicle
    return vehicle


@transaction.atomic
def update_vehicle_from_data(*, actor, vehicle: Vehicle, validated_data: dict) -> Vehicle:
    """ES: Actualiza un vehículo con bloqueo, permisos y trazabilidad de su identidad técnica.

    EN: Updates a vehicle with locking, permissions, and technical identity traceability.
    """

    vehicle = _locked_vehicle(vehicle)
    before = _vehicle_snapshot(vehicle)
    previous_status = vehicle.status
    validated_data = dict(validated_data)
    change_reason = (validated_data.pop("change_reason", "") or "").strip()
    identity_changed = any(
        field in validated_data and validated_data[field] != getattr(vehicle, field)
        for field in ("brand", "model", "year", "vin")
    )
    if identity_changed and not change_reason:
        raise ValidationError("La modificación de identidad técnica requiere una justificación.")
    if identity_changed and previous_status in COMMERCIAL_VEHICLE_STATUSES:
        raise ValidationError("No se puede modificar la identidad técnica de un vehículo reservado o vendido.")
    _require_vehicle_permission(actor=actor, code="vehicles.manage", branch=vehicle.branch)
    vehicle = _apply_vehicle_data(vehicle, validated_data)
    _require_vehicle_permission(actor=actor, code="vehicles.manage", branch=vehicle.branch)
    _validate_status_change(
        actor=actor,
        branch=vehicle.branch,
        previous=previous_status,
        new=vehicle.status,
    )
    _prepare_vehicle_identifiers(vehicle)
    if vehicle.status == Vehicle.Status.AVAILABLE and not vehicle.published_at:
        vehicle.published_at = timezone.now()
    vehicle.full_clean()
    vehicle.save()
    after = _vehicle_snapshot(vehicle)
    if change_reason:
        after["change_reason"] = change_reason
    audit_log(
        user=actor,
        action="vehicles.update",
        target=vehicle,
        branch=vehicle.branch,
        before=before,
        after=after,
    )
    return vehicle


def _ensure_status_action_allowed(vehicle: Vehicle) -> None:
    if vehicle.status in COMMERCIAL_VEHICLE_STATUSES:
        raise ValidationError("No se puede alterar un vehículo reservado o vendido desde catálogo.")


@transaction.atomic
def publish_vehicle(*, vehicle: Vehicle, actor) -> Vehicle:
    vehicle = _locked_vehicle(vehicle)
    _require_vehicle_permission(actor=actor, code="vehicles.publish", branch=vehicle.branch)
    _ensure_status_action_allowed(vehicle)
    before = _vehicle_snapshot(vehicle)
    vehicle.status = Vehicle.Status.AVAILABLE
    vehicle.published_at = timezone.now()
    vehicle.save(update_fields=["status", "published_at", "updated_at"])
    audit_log(user=actor, action="vehicles.publish", target=vehicle, branch=vehicle.branch, before=before, after=_vehicle_snapshot(vehicle))
    return vehicle


@transaction.atomic
def hide_vehicle(*, vehicle: Vehicle, actor) -> Vehicle:
    vehicle = _locked_vehicle(vehicle)
    _require_vehicle_permission(actor=actor, code="vehicles.publish", branch=vehicle.branch)
    _ensure_status_action_allowed(vehicle)
    before = _vehicle_snapshot(vehicle)
    vehicle.status = Vehicle.Status.HIDDEN
    vehicle.save(update_fields=["status", "updated_at"])
    audit_log(user=actor, action="vehicles.hide", target=vehicle, branch=vehicle.branch, before=before, after=_vehicle_snapshot(vehicle))
    return vehicle


@transaction.atomic
def archive_vehicle(*, vehicle: Vehicle, actor) -> Vehicle:
    vehicle = _locked_vehicle(vehicle)
    _require_vehicle_permission(actor=actor, code="vehicles.publish", branch=vehicle.branch)
    _ensure_status_action_allowed(vehicle)
    before = _vehicle_snapshot(vehicle)
    vehicle.status = Vehicle.Status.ARCHIVED
    vehicle.save(update_fields=["status", "updated_at"])
    audit_log(user=actor, action="vehicles.archive", target=vehicle, branch=vehicle.branch, before=before, after=_vehicle_snapshot(vehicle))
    return vehicle


@transaction.atomic
def create_brand(*, actor, form) -> VehicleBrand:
    brand = form.save()
    audit_log(user=actor, action="vehicles.brand_create", target=brand, after={"name": brand.name, "is_active": brand.is_active})
    return brand


@transaction.atomic
def create_model(*, actor, form) -> VehicleModel:
    model = form.save()
    audit_log(user=actor, action="vehicles.model_create", target=model, after={"brand": model.brand_id, "name": model.name})
    return model


def _uploaded_file_metadata(uploaded_file):
    import hashlib
    if not uploaded_file:
        return {"file_hash": "", "mime_type": ""}
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)
    digest = hashlib.sha256()
    for chunk in uploaded_file.chunks():
        digest.update(chunk)
    if hasattr(uploaded_file, "seek"):
        uploaded_file.seek(0)
    return {"file_hash": digest.hexdigest(), "mime_type": getattr(uploaded_file, "content_type", "") or ""}


@transaction.atomic
def upload_vehicle_media(*, actor, vehicle: Vehicle, form):
    from apps.vehicles.models import VehicleResource

    vehicle = _locked_vehicle(vehicle)
    _require_vehicle_permission(actor=actor, code="vehicles.manage", branch=vehicle.branch)
    uploaded_file = form.cleaned_data["file"]
    metadata = _uploaded_file_metadata(uploaded_file)
    resource_type = VehicleResource.ResourceType.IMAGE
    media_type = form.cleaned_data["media_type"]
    if media_type == VehicleMedia.MediaType.MODEL_3D:
        resource_type = VehicleResource.ResourceType.MODEL_3D
    elif media_type == VehicleMedia.MediaType.MANUAL:
        resource_type = VehicleResource.ResourceType.MANUAL
    elif media_type == VehicleMedia.MediaType.VIDEO:
        resource_type = VehicleResource.ResourceType.VIDEO

    resource = VehicleResource.objects.create(
        title=form.cleaned_data.get("title") or uploaded_file.name,
        resource_type=resource_type,
        file=uploaded_file,
        file_hash=metadata["file_hash"],
        mime_type=metadata["mime_type"],
        uploaded_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    media = VehicleMedia.objects.create(
        vehicle=vehicle,
        resource=resource,
        media_type=media_type,
        title=form.cleaned_data.get("title", ""),
        alt_text=form.cleaned_data.get("alt_text", ""),
        order=form.cleaned_data.get("order") or 0,
        is_public=form.cleaned_data.get("is_public", True),
    )
    audit_log(
        user=actor,
        action="vehicles.media.upload",
        target=vehicle,
        branch=vehicle.branch,
        after={"media_id": media.pk, "resource_id": resource.pk, "media_type": media.media_type, "file_hash": resource.file_hash},
    )
    return media


@transaction.atomic
def update_vehicle_media(*, actor, vehicle: Vehicle, media: VehicleMedia, form) -> VehicleMedia:
    """ES: Actualiza metadatos multimedia sin reemplazar el archivo almacenado.

    EN: Updates media metadata without replacing the stored file.
    """

    vehicle = _locked_vehicle(vehicle)
    _require_vehicle_permission(actor=actor, code="vehicles.manage", branch=vehicle.branch)
    media = VehicleMedia.objects.select_for_update().get(pk=media.pk, vehicle=vehicle)
    before = {field: getattr(media, field) for field in ("media_type", "title", "alt_text", "order", "is_public")}
    for field in before:
        setattr(media, field, form.cleaned_data[field])
    media.full_clean()
    media.save(update_fields=[*before, "updated_at"])
    audit_log(
        user=actor,
        action="vehicles.media.update",
        target=vehicle,
        branch=vehicle.branch,
        before=before,
        after={field: getattr(media, field) for field in before},
    )
    return media


@transaction.atomic
def remove_vehicle_media(*, actor, vehicle: Vehicle, media: VehicleMedia) -> None:
    """ES: Desvincula multimedia; conserva el recurso reutilizable y su archivo.

    EN: Unlinks media while preserving its reusable resource and stored file.
    """

    vehicle = _locked_vehicle(vehicle)
    _require_vehicle_permission(actor=actor, code="vehicles.manage", branch=vehicle.branch)
    media = VehicleMedia.objects.select_for_update().get(pk=media.pk, vehicle=vehicle)
    snapshot = {"media_id": media.pk, "resource_id": media.resource_id, "media_type": media.media_type}
    media.delete()
    audit_log(user=actor, action="vehicles.media.unlink", target=vehicle, branch=vehicle.branch, before=snapshot)


@transaction.atomic
def save_vehicle_highlight(
    *, actor, vehicle: Vehicle, form, highlight: VehicleCommercialHighlight | None = None
) -> VehicleCommercialHighlight:
    """ES: Crea o actualiza un destacado comercial auditado.

    EN: Creates or updates an audited commercial highlight.
    """

    vehicle = _locked_vehicle(vehicle)
    _require_vehicle_permission(actor=actor, code="vehicles.manage", branch=vehicle.branch)
    if highlight is None:
        highlight = VehicleCommercialHighlight(vehicle=vehicle)
        before = None
        action = "vehicles.highlight.create"
    else:
        highlight = VehicleCommercialHighlight.objects.select_for_update().get(pk=highlight.pk, vehicle=vehicle)
        before = {field: getattr(highlight, field) for field in ("title", "value", "icon", "order")}
        action = "vehicles.highlight.update"
    for field in ("title", "value", "icon", "order"):
        setattr(highlight, field, form.cleaned_data[field])
    highlight.full_clean()
    highlight.save()
    audit_log(
        user=actor,
        action=action,
        target=vehicle,
        branch=vehicle.branch,
        before=before,
        after={field: getattr(highlight, field) for field in ("title", "value", "icon", "order")},
    )
    return highlight


@transaction.atomic
def remove_vehicle_highlight(*, actor, vehicle: Vehicle, highlight: VehicleCommercialHighlight) -> None:
    vehicle = _locked_vehicle(vehicle)
    _require_vehicle_permission(actor=actor, code="vehicles.manage", branch=vehicle.branch)
    highlight = VehicleCommercialHighlight.objects.select_for_update().get(pk=highlight.pk, vehicle=vehicle)
    snapshot = {"highlight_id": highlight.pk, "title": highlight.title}
    highlight.delete()
    audit_log(user=actor, action="vehicles.highlight.delete", target=vehicle, branch=vehicle.branch, before=snapshot)


@transaction.atomic
def save_vehicle_part_specification(
    *, actor, vehicle: Vehicle, form, specification: VehiclePartSpecification | None = None
) -> VehiclePartSpecification:
    """ES: Crea o actualiza especificaciones técnicas del vehículo.

    EN: Creates or updates vehicle technical specifications.
    """

    vehicle = _locked_vehicle(vehicle)
    _require_vehicle_permission(actor=actor, code="vehicles.manage", branch=vehicle.branch)
    fields = (
        "part_code", "title", "summary", "description", "image", "specs",
        "hotspot_label", "hotspot_x", "hotspot_y", "hotspot_z", "order",
    )
    if specification is None:
        specification = VehiclePartSpecification(vehicle=vehicle)
        before = None
        action = "vehicles.specification.create"
    else:
        specification = VehiclePartSpecification.objects.select_for_update().get(
            pk=specification.pk, vehicle=vehicle
        )
        before = {
            field: (
                specification.image_id
                if field == "image"
                else str(getattr(specification, field))
                if field.startswith("hotspot_") and getattr(specification, field) is not None
                else getattr(specification, field)
            )
            for field in fields
        }
        action = "vehicles.specification.update"
    for field in fields:
        setattr(specification, field, form.cleaned_data[field])
    specification.full_clean()
    specification.save()
    after = {
        field: (
            specification.image_id
            if field == "image"
            else str(getattr(specification, field))
            if field.startswith("hotspot_") and getattr(specification, field) is not None
            else getattr(specification, field)
        )
        for field in fields
    }
    audit_log(user=actor, action=action, target=vehicle, branch=vehicle.branch, before=before, after=after)
    return specification


@transaction.atomic
def remove_vehicle_part_specification(
    *, actor, vehicle: Vehicle, specification: VehiclePartSpecification
) -> None:
    vehicle = _locked_vehicle(vehicle)
    _require_vehicle_permission(actor=actor, code="vehicles.manage", branch=vehicle.branch)
    specification = VehiclePartSpecification.objects.select_for_update().get(
        pk=specification.pk, vehicle=vehicle
    )
    snapshot = {"specification_id": specification.pk, "title": specification.title}
    specification.delete()
    audit_log(user=actor, action="vehicles.specification.delete", target=vehicle, branch=vehicle.branch, before=snapshot)


def _require_link_code_permission(*, actor, branch) -> None:
    """La gestión de códigos requiere `vehicles.link_codes` en la sucursal."""
    if actor is None:
        return
    if branch is None:
        if accessible_branch_ids(actor, permission_codes=("vehicles.link_codes",)) is not None:
            raise ValidationError("No tienes alcance global para gestionar códigos de vinculación sin sucursal.")
        return
    if not actor.has_perm_code("vehicles.link_codes", branch=branch):
        raise ValidationError("No tienes permiso para gestionar códigos de vinculación en esta sucursal.")


def _compact_link_code(value: str) -> str:
    return re.sub(r"[^A-Z0-9]+", "", (value or "").upper())


def _link_code_lookup_pattern(value: str) -> str | None:
    try:
        canonical = VehicleLinkCode.normalize_input(value)
    except ValidationError:
        return None
    compact = _compact_link_code(canonical)
    separator = r"[\s\-]*"
    return "^" + separator.join(re.escape(char) for char in compact) + "$"


def _customer_vehicle_snapshot(link: CustomerVehicle, *, active: bool) -> dict:
    return {
        "customer": link.customer_id,
        "vehicle": link.vehicle_id,
        "active": active,
        "snapshot_customer_name": link.snapshot_customer_name,
        "snapshot_identification": link.snapshot_identification,
        "unlinked_at": link.unlinked_at.isoformat() if link.unlinked_at else None,
    }


@transaction.atomic
def generate_vehicle_link_code(*, actor, vehicle: Vehicle, expires_after_days: int | None = None) -> VehicleLinkCode:
    vehicle = _locked_vehicle(vehicle)
    _require_link_code_permission(actor=actor, branch=vehicle.branch)
    for active in VehicleLinkCode.objects.select_for_update().filter(vehicle=vehicle, status=VehicleLinkCode.Status.ACTIVE):
        before = {"code_mask": active.masked, "status": VehicleLinkCode.Status.ACTIVE}
        active.status = VehicleLinkCode.Status.REVOKED
        active.revoked_by = actor if getattr(actor, "is_authenticated", False) else None
        active.revocation_reason = "Reemplazado por un nuevo código."
        active.save(update_fields=["status", "revoked_by", "revocation_reason", "updated_at"])
        audit_log(
            user=actor,
            action="vehicles.link_code.revoke",
            target=vehicle,
            branch=vehicle.branch,
            before=before,
            after={"code_mask": active.masked, "status": VehicleLinkCode.Status.REVOKED},
            is_sensitive=True,
        )
    expires_at = None
    if expires_after_days:
        expires_at = timezone.now() + timedelta(days=expires_after_days)
    code_obj = VehicleLinkCode.objects.create(
        vehicle=vehicle,
        code=VehicleLinkCode.generate_new_code(),
        expires_at=expires_at,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
    )
    audit_log(
        user=actor,
        action="vehicles.link_code.generate",
        target=vehicle,
        branch=vehicle.branch,
        after={"code_mask": code_obj.masked, "expires_at": expires_at.isoformat() if expires_at else None},
        is_sensitive=True,
    )
    return code_obj


@transaction.atomic
def revoke_vehicle_link_code(*, actor, link_code: VehicleLinkCode, reason: str = "") -> VehicleLinkCode:
    code_obj = VehicleLinkCode.objects.select_for_update().select_related("vehicle").get(pk=link_code.pk)
    _require_link_code_permission(actor=actor, branch=code_obj.vehicle.branch)
    if code_obj.status == VehicleLinkCode.Status.USED:
        raise ValidationError("El código ya fue utilizado; desactiva la vinculación del cliente en el garaje.")
    if code_obj.status == VehicleLinkCode.Status.REVOKED:
        raise ValidationError("El código ya fue revocado.")
    before = {"code_mask": code_obj.masked, "status": code_obj.status}
    code_obj.status = VehicleLinkCode.Status.REVOKED
    code_obj.revoked_by = actor if getattr(actor, "is_authenticated", False) else None
    code_obj.revocation_reason = reason
    code_obj.save(update_fields=["status", "revoked_by", "revocation_reason", "updated_at"])
    audit_log(
        user=actor,
        action="vehicles.link_code.revoke",
        target=code_obj.vehicle,
        branch=code_obj.vehicle.branch,
        before=before,
        after={"code_mask": code_obj.masked, "status": VehicleLinkCode.Status.REVOKED},
        is_sensitive=True,
    )
    return code_obj


@transaction.atomic
def redeem_link_code(*, actor=None, customer, code: str) -> CustomerVehicle:
    """Canje atómico de un código privado por parte del cliente (garaje).

    Serializa la operación con advisory lock sobre el código y bloquea filas
    (`select_for_update`) para impedir doble canje y doble propietario activo.
    """
    if customer is None or not getattr(customer, "pk", None):
        raise ValidationError("No se identificó un expediente de cliente para el canje.")
    pattern = _link_code_lookup_pattern(code)
    if not pattern:
        raise ValidationError("El código de vinculación no tiene un formato válido.")
    acquire_transaction_advisory_lock(namespace="vehicle-link-codes", value=_compact_link_code(code))
    code_obj = (
        VehicleLinkCode.objects.select_for_update()
        .select_related("vehicle")
        .filter(code__iregex=pattern)
        .first()
    )
    if code_obj is None:
        raise ValidationError("El código de vinculación no es válido o ya no está disponible.")
    if code_obj.status != VehicleLinkCode.Status.ACTIVE:
        raise ValidationError("El código de vinculación ya fue utilizado o revocado.")
    if code_obj.is_expired:
        raise ValidationError("El código de vinculación caducó. Solicita uno nuevo a la concesionaria.")
    vehicle = Vehicle.objects.select_for_update().get(pk=code_obj.vehicle_id, is_deleted=False)
    existing_active = CustomerVehicle.objects.select_for_update().filter(vehicle=vehicle, is_active=True).first()
    if existing_active is not None:
        if existing_active.customer_id == customer.pk:
            raise ValidationError("Este vehículo ya está vinculado a tu garaje.")
        raise ValidationError("El vehículo ya está vinculado a otro cliente. Solicita la transferencia a la concesionaria.")
    link = CustomerVehicle.objects.create(
        customer=customer,
        vehicle=vehicle,
        linked_via=code_obj,
        initial_mileage=vehicle.mileage,
        snapshot_customer_name=customer.display_name,
        snapshot_identification=customer.identification_number or "",
        is_active=True,
    )
    code_obj.status = VehicleLinkCode.Status.USED
    code_obj.used_by = customer
    code_obj.used_at = timezone.now()
    code_obj.save(update_fields=["status", "used_by", "used_at", "updated_at"])
    audit_log(
        user=actor if getattr(actor, "is_authenticated", False) else None,
        action="vehicles.link_code.redeemed",
        target=link,
        customer=customer,
        branch=vehicle.branch,
        before={"code_mask": code_obj.masked, "status": VehicleLinkCode.Status.ACTIVE},
        after={
            "code_mask": code_obj.masked,
            "status": VehicleLinkCode.Status.USED,
            "vehicle": vehicle.pk,
            "customer": customer.pk,
        },
        is_sensitive=True,
    )
    from apps.notifications.services import schedule_customer_event_notification

    schedule_customer_event_notification(
        customer=customer,
        title="Vehículo agregado a tu garaje",
        body=f"{vehicle} ya está disponible en tu garaje privado.",
        message_type="alert",
        dedup_key=f"vehicle-link:{link.pk}:redeemed",
        actor=actor,
        branch=vehicle.branch,
        related_vehicle=vehicle,
    )
    return link


@transaction.atomic
def unlink_customer_vehicle(*, actor, link: CustomerVehicle, reason: str = "") -> CustomerVehicle:
    """Desactiva un vínculo activo conservando el historial (archivado)."""
    link = CustomerVehicle.objects.select_for_update().select_related("vehicle", "customer").get(pk=link.pk)
    _require_link_code_permission(actor=actor, branch=link.vehicle.branch)
    if not link.is_active:
        raise ValidationError("El vínculo ya está inactivo.")
    link.refresh_snapshots()
    before = _customer_vehicle_snapshot(link, active=True)
    link.is_active = False
    link.unlinked_at = timezone.now()
    link.unlinked_reason = reason
    link.save(update_fields=["is_active", "unlinked_at", "unlinked_reason", "snapshot_customer_name", "snapshot_identification", "updated_at"])
    audit_log(
        user=actor,
        action="vehicles.customer_vehicle.unlink",
        target=link,
        branch=link.vehicle.branch,
        before=before,
        after=_customer_vehicle_snapshot(link, active=False),
        severity="medium",
    )
    return link


@transaction.atomic
def transfer_customer_vehicle(*, actor, link: CustomerVehicle, new_customer: Customer, reason: str = "") -> CustomerVehicle:
    """Cambio de titular: desactiva el propietario actual y vincula el nuevo.

    Preserva el historial técnico del vehículo y jamás traslada los documentos
    privados del propietario anterior al nuevo.
    """
    link = CustomerVehicle.objects.select_for_update().select_related("vehicle", "customer").get(pk=link.pk)
    _require_link_code_permission(actor=actor, branch=link.vehicle.branch)
    if not link.is_active:
        raise ValidationError("El vínculo del titular actual ya está inactivo.")
    if new_customer is None or not getattr(new_customer, "pk", None):
        raise ValidationError("Selecciona el nuevo titular.")
    if new_customer.pk == link.customer_id:
        raise ValidationError("El nuevo titular ya es el titular actual.")
    vehicle = Vehicle.objects.select_for_update().get(pk=link.vehicle_id, is_deleted=False)
    former_owner = link.customer_id

    link.refresh_snapshots()
    before = _customer_vehicle_snapshot(link, active=True)
    link.is_active = False
    link.unlinked_at = timezone.now()
    link.unlinked_reason = reason or "Transferencia de titularidad"
    link.save(update_fields=["is_active", "unlinked_at", "unlinked_reason", "snapshot_customer_name", "snapshot_identification", "updated_at"])
    audit_log(
        user=actor,
        action="vehicles.customer_vehicle.unlink",
        target=link,
        branch=vehicle.branch,
        before=before,
        after=_customer_vehicle_snapshot(link, active=False),
        metadata={"reason": reason or "transferencia de titularidad"},
        severity="medium",
    )
    new_link = CustomerVehicle.objects.create(
        customer=new_customer,
        vehicle=vehicle,
        role_type=CustomerVehicle.RoleType.OWNER,
        linked_via=None,
        initial_mileage=vehicle.mileage,
        snapshot_customer_name=new_customer.display_name,
        snapshot_identification=new_customer.identification_number or "",
        is_active=True,
    )
    audit_log(
        user=actor,
        action="vehicles.customer_vehicle.transfer",
        target=new_link,
        branch=vehicle.branch,
        before={"previous_customer": former_owner, "vehicle": vehicle.pk},
        after={"new_customer": new_customer.pk, "vehicle": vehicle.pk},
        metadata={"reason": reason or "transferencia de titularidad"},
        severity="medium",
    )
    return new_link
