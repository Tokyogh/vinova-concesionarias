"""ES: Este módulo orquesta servicios de aplicación y transacciones para el dominio de importaciones.

EN: This module orchestrates application services and transactions for the imports domain.

Contexto existente / Existing context:
Application support for the imports domain.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.text import slugify

from apps.audit.services import audit_log
from apps.branches.models import Branch
from apps.customers.models import Customer
from apps.imports.models import ImportBatch, ImportRow
from apps.imports.parsing import MAX_PREVIEW_ROWS, NORMALIZERS, calculate_file_hash, read_import_rows
from apps.inventory.models import BranchStock, InventoryCategory, InventoryItem, StockMovement
from apps.vehicles.models import (
    Vehicle,
    VehicleBrand,
    VehicleCommercialHighlight,
    VehicleModel,
    VehiclePartSpecification,
)

logger = logging.getLogger(__name__)


@transaction.atomic
def create_import_batch(*, actor, import_type: str, uploaded_file, notes: str = "", default_branch=None, require_vehicle_branch: bool = False) -> ImportBatch:
    """Persiste y valida un lote, retirando residuos rechazados atómicamente.

    Persists and validates a batch, atomically removing rejected temporary artifacts.
    """

    batch = ImportBatch.objects.create(
        import_type=import_type,
        original_file=uploaded_file,
        original_filename=getattr(uploaded_file, "name", "importacion"),
        file_hash=calculate_file_hash(uploaded_file),
        file_size=getattr(uploaded_file, "size", 0) or 0,
        uploaded_by=actor if getattr(actor, "is_authenticated", False) else None,
        default_branch=default_branch,
        require_vehicle_branch=bool(require_vehicle_branch),
        notes=notes,
    )
    audit_log(user=actor, action="imports.batch.upload", target=batch, after={"import_type": import_type, "file_name": batch.original_filename, "file_hash": batch.file_hash, "default_branch": getattr(default_branch, "pk", None), "require_vehicle_branch": bool(require_vehicle_branch)})
    try:
        validate_import_batch(batch=batch, actor=actor)
    except Exception:
        try:
            batch.original_file.delete(save=False)
        except Exception as cleanup_error:  # noqa: BLE001 - ES/EN: preserve the original validation failure
            logger.warning("No se pudo retirar el archivo de una importación rechazada (%s).", cleanup_error.__class__.__name__)
        raise
    return batch


@transaction.atomic
def validate_import_batch(*, batch: ImportBatch, actor=None) -> ImportBatch:
    """Parse and validate every row while recording an auditable batch result."""

    rows = read_import_rows(batch)
    batch.rows.all().delete()
    normalizer = NORMALIZERS[batch.import_type]
    invalid = 0
    valid = 0
    errors: list[dict[str, Any]] = []
    preview: list[dict[str, Any]] = []

    normalized_rows: list[dict[str, Any]] = []
    for index, payload in enumerate(rows, start=2):  # 1 = header
        normalized, row_errors = normalizer(payload, batch=batch)
        normalized_rows.append(
            {
                "index": index,
                "payload": payload,
                "normalized": normalized,
                "errors": list(row_errors),
            }
        )

    if batch.import_type == ImportBatch.ImportType.VEHICLES:
        for field_name, label in (("vin", "VIN"), ("internal_code", "código interno")):
            grouped: dict[str, list[dict[str, Any]]] = {}
            for item in normalized_rows:
                value = (item["normalized"].get(field_name) or "").strip().upper()
                if value:
                    grouped.setdefault(value, []).append(item)
            for value, duplicated in grouped.items():
                if len(duplicated) > 1:
                    row_numbers = ", ".join(str(item["index"]) for item in duplicated)
                    message = f"{label.upper() if label == 'VIN' else label.capitalize()} duplicado dentro del archivo ({value}) en las filas {row_numbers}. Debe aparecer una sola vez."
                    for item in duplicated:
                        item["errors"].append(message)

    for item in normalized_rows:
        index = item["index"]
        payload = item["payload"]
        normalized = item["normalized"]
        row_errors = item["errors"]
        status = ImportRow.RowStatus.INVALID if row_errors else ImportRow.RowStatus.VALID
        if row_errors:
            invalid += 1
            errors.append({"row": index, "errors": row_errors})
        else:
            valid += 1
        ImportRow.objects.create(
            batch=batch,
            row_number=index,
            status=status,
            payload=payload,
            normalized_payload=normalized,
            errors=row_errors,
        )
        if len(preview) < MAX_PREVIEW_ROWS:
            preview.append(
                {
                    "row": index,
                    "status": status,
                    "payload": payload,
                    "normalized": normalized,
                    "errors": row_errors,
                }
            )

    if not rows:
        invalid = 1
        errors = [{"row": "archivo", "errors": ["El archivo no contiene filas de datos para importar."]}]

    batch.total_rows = len(rows)
    batch.valid_rows = valid
    batch.invalid_rows = invalid
    batch.error_count = invalid
    batch.preview_rows = preview
    batch.errors = errors[:100]
    batch.status = ImportBatch.Status.VALIDATED if invalid == 0 and valid > 0 else ImportBatch.Status.FAILED
    batch.validated_at = timezone.now()
    batch.save(
        update_fields=[
            "total_rows",
            "valid_rows",
            "invalid_rows",
            "error_count",
            "preview_rows",
            "errors",
            "status",
            "validated_at",
            "updated_at",
        ]
    )
    audit_log(
        user=actor,
        action="imports.batch.validate",
        target=batch,
        after={"rows": batch.total_rows, "valid": valid, "invalid": invalid},
    )
    return batch


def _vehicle_slug(*, brand: VehicleBrand, model: VehicleModel, year: int, version: str, reference: str = "") -> str:
    base = slugify(f"{year}-{brand.name}-{model.name}-{version or reference or 'vehiculo'}")[:150] or "vehiculo"
    candidate = base
    counter = 2
    while Vehicle.objects.filter(public_slug=candidate).exists():
        suffix = f"-{counter}"
        candidate = f"{base[:180-len(suffix)]}{suffix}"
        counter += 1
    return candidate


def _get_or_create_vehicle_brand(name: str) -> VehicleBrand:
    brand = VehicleBrand.objects.filter(name__iexact=name).first()
    if brand:
        if not brand.is_active:
            brand.is_active = True
            brand.save(update_fields=["is_active", "updated_at"])
        return brand
    return VehicleBrand.objects.create(name=name, is_active=True)


def _get_or_create_vehicle_model(*, brand: VehicleBrand, name: str) -> VehicleModel:
    model = VehicleModel.objects.filter(brand=brand, name__iexact=name).first()
    if model:
        if not model.is_active:
            model.is_active = True
            model.save(update_fields=["is_active", "updated_at"])
        return model
    return VehicleModel.objects.create(brand=brand, name=name, is_active=True)


def _import_vehicle_snapshot(vehicle: Vehicle) -> dict[str, Any]:
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
        "price": str(vehicle.price) if vehicle.price is not None else None,
        "status": vehicle.status,
        "is_featured": vehicle.is_featured,
        "published_at": vehicle.published_at.isoformat() if vehicle.published_at else None,
    }


def _sync_vehicle_catalog_details(vehicle: Vehicle, data: dict[str, Any]) -> None:
    """Actualiza datos comerciales importados sin tocar multimedia.

    Las fotos, videos, modelo 3D, manuales y galerías se administran desde la
    ficha del vehículo. La importación solo llena datos estructurados del
    catálogo para que las cards/fichas públicas se alimenten desde la BD.
    """
    for order, (part_code, detail) in enumerate((data.get("part_specs") or {}).items(), start=1):
        spec = vehicle.part_specs.filter(part_code=part_code, title=detail.get("title") or dict(VehiclePartSpecification.PartCode.choices).get(part_code, "Especificación")).first()
        defaults = {
            "summary": (detail.get("description") or "")[:220],
            "description": detail.get("description") or "",
            "order": order,
        }
        if spec:
            for field, value in defaults.items():
                setattr(spec, field, value)
            spec.save(update_fields=["summary", "description", "order", "updated_at"])
        else:
            VehiclePartSpecification.objects.create(vehicle=vehicle, part_code=part_code, title=detail.get("title") or "Especificación", **defaults)

    for order, item in enumerate(data.get("highlights") or [], start=1):
        highlight = vehicle.highlights.filter(title__iexact=item["title"]).first()
        defaults = {"value": item.get("value", ""), "icon": "import", "order": order}
        if highlight:
            for field, value in defaults.items():
                setattr(highlight, field, value)
            highlight.save(update_fields=["value", "icon", "order", "updated_at"])
        else:
            VehicleCommercialHighlight.objects.create(vehicle=vehicle, title=item["title"], **defaults)


def _apply_vehicle(row: ImportRow, actor) -> tuple[str, Vehicle]:
    data = row.normalized_payload
    brand = _get_or_create_vehicle_brand(data["brand"])
    model = _get_or_create_vehicle_model(brand=brand, name=data["model"])
    branch = Branch.objects.filter(pk=data.get("branch_id")).first() if data.get("branch_id") else None
    status = data.get("status") or Vehicle.Status.AVAILABLE
    defaults = {
        "brand": brand,
        "model": model,
        "branch": branch,
        "year": data["year"],
        "version": data.get("version", ""),
        "plate": data.get("plate", ""),
        "color": data.get("color", ""),
        "mileage": data.get("mileage") or 0,
        "price": Decimal(data["price"]) if data.get("price") is not None else None,
        "status": status,
        "short_description": data.get("short_description", ""),
        "description": data.get("description", ""),
        "is_featured": data.get("is_featured", False),
    }
    if data.get("vin"):
        defaults["vin"] = data["vin"]
    vehicle = None
    if data.get("internal_code"):
        vehicle = Vehicle.objects.filter(internal_code__iexact=data["internal_code"], is_deleted=False).first()
    if vehicle is None and data.get("vin"):
        vehicle = Vehicle.objects.filter(vin__iexact=data["vin"], is_deleted=False).first()
    if vehicle:
        before = _import_vehicle_snapshot(vehicle)
        defaults["published_at"] = (
            vehicle.published_at or timezone.now()
            if data.get("publish_catalog") and status == Vehicle.Status.AVAILABLE
            else None
        )
        for field, value in defaults.items():
            setattr(vehicle, field, value)
        vehicle.full_clean()
        vehicle.save()
        _sync_vehicle_catalog_details(vehicle, data)
        audit_log(
            user=actor,
            action="imports.vehicle.update",
            target=vehicle,
            before=before,
            after=_import_vehicle_snapshot(vehicle),
            metadata={"batch_id": row.batch_id, "row_number": row.row_number},
        )
        return "updated", vehicle
    defaults["published_at"] = timezone.now() if data.get("publish_catalog") and status == Vehicle.Status.AVAILABLE else None
    vehicle = Vehicle(
        internal_code=data.get("internal_code", ""),
        public_slug="pending",
        **defaults,
    )
    vehicle.full_clean()
    vehicle.save()  # genera automáticamente internal_code cuando viene vacío
    vehicle.public_slug = _vehicle_slug(
        brand=brand,
        model=model,
        year=data["year"],
        version=data.get("version", ""),
        reference=vehicle.internal_code,
    )
    vehicle.save(update_fields=["public_slug", "updated_at"])
    _sync_vehicle_catalog_details(vehicle, data)
    audit_log(
        user=actor,
        action="imports.vehicle.create",
        target=vehicle,
        after=_import_vehicle_snapshot(vehicle),
        metadata={"batch_id": row.batch_id, "row_number": row.row_number},
    )
    return "created", vehicle


def _apply_customer(row: ImportRow, actor) -> tuple[str, Customer]:
    data = row.normalized_payload
    lookup = {}
    if data.get("identification_number"):
        lookup = {"identification_number": data["identification_number"]}
    elif data.get("email"):
        lookup = {"email": data["email"]}
    customer = Customer.objects.filter(**lookup).first() if lookup else None
    defaults = {k: v for k, v in data.items() if k in {"customer_type", "identification_type", "identification_number", "first_name", "last_name", "business_name", "email", "phone", "whatsapp", "address", "city", "province", "source", "status"}}
    if customer:
        for field, value in defaults.items():
            setattr(customer, field, value)
        customer.full_clean()
        customer.save()
        return "updated", customer
    customer = Customer(created_by=actor if getattr(actor, "is_authenticated", False) else None, **defaults)
    customer.full_clean()
    customer.save()
    return "created", customer


def _apply_inventory(row: ImportRow, actor) -> tuple[str, InventoryItem]:
    data = row.normalized_payload
    category = None
    if data.get("category"):
        category, _ = InventoryCategory.objects.get_or_create(name=data["category"], defaults={"slug": slugify(data["category"]), "is_active": True})
    defaults = {
        "category": category,
        "name": data["name"],
        "item_type": data["item_type"],
        "description": data.get("description", ""),
        "unit": data.get("unit") or "unidad",
        "price": Decimal(data["price"]),
        "cost": Decimal(data["cost"]) if data.get("cost") is not None else None,
        "status": data.get("status") or InventoryItem.Status.ACTIVE,
        "is_public": data.get("is_public", False),
        "track_stock": data.get("track_stock", True),
    }
    item = InventoryItem.objects.filter(sku=data["sku"]).first()
    if item:
        for field, value in defaults.items():
            setattr(item, field, value)
        item.full_clean()
        item.save()
        return "updated", item
    item = InventoryItem(
        sku=data["sku"],
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
        **defaults,
    )
    item.full_clean()
    item.save()
    return "created", item


def _apply_stock(row: ImportRow, actor) -> tuple[str, BranchStock]:
    data = row.normalized_payload
    item = InventoryItem.objects.get(sku=data["sku"])
    branch = Branch.objects.get(pk=data["branch_id"])
    quantity = Decimal(data["quantity"])
    minimum_stock = Decimal(data["minimum_stock"])
    stock, created = BranchStock.objects.select_for_update().get_or_create(item=item, branch=branch)
    previous = stock.quantity
    stock.quantity = quantity
    stock.minimum_stock = minimum_stock
    stock.location_code = data.get("location_code", "")
    stock.last_movement_at = timezone.now()
    stock.full_clean()
    stock.save()
    StockMovement.objects.create(
        item=item,
        branch=branch,
        movement_type=StockMovement.MovementType.ADJUST,
        quantity=quantity,
        previous_quantity=previous,
        new_quantity=quantity,
        reference=data.get("reference") or "Importación masiva",
        reason="Ajuste generado desde importación masiva.",
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
        confirmed_at=timezone.now(),
    )
    return "created" if created else "updated", stock


APPLIERS = {
    ImportBatch.ImportType.VEHICLES: _apply_vehicle,
    ImportBatch.ImportType.CUSTOMERS: _apply_customer,
    ImportBatch.ImportType.INVENTORY: _apply_inventory,
    ImportBatch.ImportType.STOCK: _apply_stock,
}


def confirm_import_batch(*, batch: ImportBatch, actor) -> ImportBatch:
    if not batch.can_confirm:
        raise ValidationError("El lote no puede confirmarse: debe estar validado y sin errores.")
    batch.status = ImportBatch.Status.PROCESSING
    batch.confirmed_by = actor if getattr(actor, "is_authenticated", False) else None
    batch.confirmed_at = timezone.now()
    batch.save(update_fields=["status", "confirmed_by", "confirmed_at", "updated_at"])

    created = updated = skipped = failed = 0
    errors = []
    applier = APPLIERS[batch.import_type]
    for row in batch.rows.select_for_update().order_by("row_number"):
        try:
            action, obj = applier(row, actor)
            if action == "created":
                created += 1
                row.status = ImportRow.RowStatus.CREATED
            elif action == "updated":
                updated += 1
                row.status = ImportRow.RowStatus.UPDATED
            else:
                skipped += 1
                row.status = ImportRow.RowStatus.SKIPPED
            row.action = action
            row.object_label = f"{obj._meta.app_label}.{obj._meta.model_name}"
            row.object_id = str(obj.pk)
            row.save(update_fields=["status", "action", "object_label", "object_id", "updated_at"])
        except Exception as exc:  # keep row-level failure trace for admin
            failed += 1
            row.status = ImportRow.RowStatus.FAILED
            row.errors = [str(exc)]
            row.save(update_fields=["status", "errors", "updated_at"])
            errors.append({"row": row.row_number, "errors": [str(exc)]})

    batch.created_count = created
    batch.updated_count = updated
    batch.skipped_count = skipped
    batch.error_count = failed
    batch.errors = errors
    batch.result_summary = {"created": created, "updated": updated, "skipped": skipped, "failed": failed}
    batch.status = ImportBatch.Status.COMPLETED if failed == 0 else ImportBatch.Status.FAILED
    batch.completed_at = timezone.now()
    batch.save(update_fields=["created_count", "updated_count", "skipped_count", "error_count", "errors", "result_summary", "status", "completed_at", "updated_at"])
    audit_log(user=actor, action="imports.batch.confirm", target=batch, after=batch.result_summary)
    return batch
