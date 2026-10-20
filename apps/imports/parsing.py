"""ES: Este módulo implementa el componente parsing para el dominio de importaciones.

EN: This module implements the parsing component for the imports domain.

Contexto existente / Existing context:
Parsing support for the imports domain.
"""

from __future__ import annotations

import csv
import hashlib
import io
import unicodedata
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from openpyxl import load_workbook

from apps.branches.models import Branch
from apps.common.validators import (
    validate_human_name,
    validate_no_unsafe_control_characters,
    validate_nonnegative_decimal,
    validate_phone_number,
    validate_vehicle_identifier,
    validate_vehicle_plate,
    validate_vehicle_year,
)
from apps.customers.identification import validate_identification_value
from apps.customers.models import Customer
from apps.imports.models import ImportBatch
from apps.inventory.models import InventoryItem
from apps.vehicles.models import Vehicle, VehiclePartSpecification
MAX_PREVIEW_ROWS = 20
MIN_VEHICLE_YEAR = 1886
MAX_VEHICLE_YEAR_OFFSET = 2

VEHICLE_REQUIRED_HEADERS = {"marca", "modelo", "año"}

HEADER_ALIASES = {
    "año": "year",
    "ano": "year",
    "anio": "year",
    "year": "year",
    "marca": "brand",
    "brand": "brand",
    "modelo": "model",
    "model": "model",
    "version": "version",
    "versión": "version",
    "vin": "vin",
    "chasis": "vin",
    "numero_chasis": "vin",
    "codigo_interno": "internal_code",
    "codigo_catalogo": "internal_code",
    "referencia_vehiculo": "internal_code",
    "placa": "plate",
    "plate": "plate",
    "color": "color",
    "kilometraje": "mileage",
    "km": "mileage",
    "precio": "price",
    "price": "price",
    "estado": "status",
    "status": "status",
    "descripcion": "description",
    "descripción": "description",
    "resumen": "short_description",
    "descripcion_corta": "short_description",
    "descripcion_publica": "description",
    "descripcion_comercial": "description",
    "publicar_en_catalogo": "publish_catalog",
    "publicado": "publish_catalog",
    "destacado": "is_featured",
    "destacado_catalogo": "is_featured",
    "motor": "engine",
    "transmision": "transmission",
    "transmisión": "transmission",
    "seguridad": "safety",
    "interior": "interior",
    "tecnologia": "technology",
    "tecnología": "technology",
    "suspension": "suspension",
    "suspensión": "suspension",
    "exterior": "exterior",
    "capacidad": "capacity",
    "capacidad_carga": "cargo",
    "garantia": "warranty",
    "garantía": "warranty",
    "consumo": "consumption",
    "etiquetas": "tags",
    "sucursal": "branch",
    "sucursal_codigo": "branch_code",
    "codigo_sucursal": "branch_code",
    "branch": "branch",
    "branch_code": "branch_code",
    "tipo": "customer_type",
    "tipo_cliente": "customer_type",
    "identificacion_tipo": "identification_type",
    "tipo_identificacion": "identification_type",
    "identificacion": "identification_number",
    "cedula": "identification_number",
    "cédula": "identification_number",
    "ruc": "identification_number",
    "pasaporte": "identification_number",
    "nombres": "first_name",
    "nombre": "first_name",
    "first_name": "first_name",
    "apellidos": "last_name",
    "apellido": "last_name",
    "last_name": "last_name",
    "razon_social": "business_name",
    "razón_social": "business_name",
    "empresa": "business_name",
    "email": "email",
    "correo": "email",
    "telefono": "phone",
    "teléfono": "phone",
    "phone": "phone",
    "whatsapp": "whatsapp",
    "direccion": "address",
    "dirección": "address",
    "ciudad": "city",
    "city": "city",
    "provincia": "province",
    "province": "province",
    "fuente": "source",
    "origen": "source",
    "sku": "sku",
    "articulo": "name",
    "artículo": "name",
    "producto": "name",
    "nombre_articulo": "name",
    "categoria": "category",
    "categoría": "category",
    "tipo_articulo": "item_type",
    "tipo_producto": "item_type",
    "unidad": "unit",
    "unit": "unit",
    "costo": "cost",
    "cost": "cost",
    "publico": "is_public",
    "público": "is_public",
    "is_public": "is_public",
    "controla_stock": "track_stock",
    "track_stock": "track_stock",
    "cantidad": "quantity",
    "stock": "quantity",
    "stock_minimo": "minimum_stock",
    "stock_mínimo": "minimum_stock",
    "minimum_stock": "minimum_stock",
    "ubicacion": "location_code",
    "ubicación": "location_code",
    "location": "location_code",
    "referencia": "reference",
    "reference": "reference",
}

VEHICLE_STATUS_MAP = {
    "disponible": Vehicle.Status.AVAILABLE,
    "available": Vehicle.Status.AVAILABLE,
    "reservado": Vehicle.Status.RESERVED,
    "reserved": Vehicle.Status.RESERVED,
    "vendido": Vehicle.Status.SOLD,
    "sold": Vehicle.Status.SOLD,
    "mantenimiento": Vehicle.Status.MAINTENANCE,
    "en mantenimiento": Vehicle.Status.MAINTENANCE,
    "oculto": Vehicle.Status.HIDDEN,
    "hidden": Vehicle.Status.HIDDEN,
    "archivado": Vehicle.Status.ARCHIVED,
    "archived": Vehicle.Status.ARCHIVED,
}

CUSTOMER_TYPE_MAP = {
    "natural": Customer.CustomerType.NATURAL,
    "persona natural": Customer.CustomerType.NATURAL,
    "empresa": Customer.CustomerType.COMPANY,
    "company": Customer.CustomerType.COMPANY,
    "juridica": Customer.CustomerType.COMPANY,
    "jurídica": Customer.CustomerType.COMPANY,
}

IDENTIFICATION_MAP = {
    "cedula": Customer.IdentificationType.CEDULA,
    "cédula": Customer.IdentificationType.CEDULA,
    "ruc": Customer.IdentificationType.RUC,
    "pasaporte": Customer.IdentificationType.PASSPORT,
    "passport": Customer.IdentificationType.PASSPORT,
    "otro": Customer.IdentificationType.OTHER,
}

CUSTOMER_STATUS_MAP = {
    "prospecto": Customer.Status.PROSPECT,
    "prospect": Customer.Status.PROSPECT,
    "activo": Customer.Status.ACTIVE,
    "active": Customer.Status.ACTIVE,
    "vip": Customer.Status.VIP,
    "inactivo": Customer.Status.INACTIVE,
    "inactive": Customer.Status.INACTIVE,
    "archivado": Customer.Status.ARCHIVED,
    "archived": Customer.Status.ARCHIVED,
}

ITEM_TYPE_MAP = {
    "aceite": InventoryItem.ItemType.OIL,
    "oil": InventoryItem.ItemType.OIL,
    "filtro": InventoryItem.ItemType.FILTER,
    "filter": InventoryItem.ItemType.FILTER,
    "repuesto": InventoryItem.ItemType.SPARE_PART,
    "spare_part": InventoryItem.ItemType.SPARE_PART,
    "accesorio": InventoryItem.ItemType.ACCESSORY,
    "accessory": InventoryItem.ItemType.ACCESSORY,
    "servicio": InventoryItem.ItemType.SERVICE,
    "service": InventoryItem.ItemType.SERVICE,
    "mantenimiento": InventoryItem.ItemType.MAINTENANCE,
    "maintenance": InventoryItem.ItemType.MAINTENANCE,
    "otro": InventoryItem.ItemType.OTHER,
    "other": InventoryItem.ItemType.OTHER,
}

ITEM_STATUS_MAP = {
    "activo": InventoryItem.Status.ACTIVE,
    "active": InventoryItem.Status.ACTIVE,
    "inactivo": InventoryItem.Status.INACTIVE,
    "inactive": InventoryItem.Status.INACTIVE,
    "archivado": InventoryItem.Status.ARCHIVED,
    "archived": InventoryItem.Status.ARCHIVED,
}


def normalize_key(value: Any) -> str:
    value = str(value or "").strip().lower().replace(" ", "_").replace("-", "_")
    value = "".join(ch for ch in unicodedata.normalize("NFD", value) if unicodedata.category(ch) != "Mn")
    return HEADER_ALIASES.get(value, value)


def clean_cell(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return str(value).strip()


def to_decimal(value: Any, default: Decimal | None = None) -> Decimal | None:
    raw = clean_cell(value).replace("$", "").replace(",", "")
    if raw == "":
        return default
    try:
        numeric = Decimal(raw)
    except (InvalidOperation, ValueError) as exc:
        raise ValidationError(f"Valor decimal inválido: {value}") from exc
    if not numeric.is_finite():
        raise ValidationError(f"Valor decimal inválido: {value}")
    return numeric


def to_int(value: Any, default: int | None = None) -> int | None:
    raw = clean_cell(value)
    if raw == "":
        return default
    try:
        numeric = Decimal(raw)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValidationError(f"Valor entero inválido: {value}") from exc
    if not numeric.is_finite() or numeric != numeric.to_integral_value():
        raise ValidationError(f"Valor entero inválido: {value}")
    return int(numeric)


def _collect_validation(errors: list[str], validator, value) -> None:
    """ES: Convierte errores Django en errores de fila. EN: Collects row-level validator errors."""

    try:
        validator(value)
    except ValidationError as exc:
        errors.extend(exc.messages)


def to_bool(value: Any, default: bool = False) -> bool:
    raw = clean_cell(value).lower()
    if raw == "":
        return default
    return raw in {"1", "si", "sí", "true", "yes", "y", "publico", "público", "activo"}


def to_bool_strict(value: Any, *, default: bool = False, field_label: str = "valor") -> bool:
    raw = clean_cell(value).lower()
    if raw == "":
        return default
    truthy = {"1", "si", "sí", "true", "yes", "y", "publico", "público", "activo"}
    falsy = {"0", "no", "false", "n", "inactivo", "privado"}
    if raw in truthy:
        return True
    if raw in falsy:
        return False
    raise ValidationError(f"{field_label}: usa únicamente sí o no.")


def calculate_file_hash(file_obj) -> str:
    digest = hashlib.sha256()
    if hasattr(file_obj, "seek"):
        file_obj.seek(0)
    for chunk in file_obj.chunks():
        digest.update(chunk)
    if hasattr(file_obj, "seek"):
        file_obj.seek(0)
    return digest.hexdigest()


def read_import_rows(batch: ImportBatch) -> list[dict[str, str]]:
    """Lee CSV/XLSX acotados sin materializar hojas ilimitadas.

    Reads bounded CSV/XLSX payloads without materializing unbounded worksheets.
    """

    suffix = Path(batch.original_file.name).suffix.lower()
    max_rows = settings.VINOVA_IMPORT_MAX_ROWS
    max_columns = settings.VINOVA_IMPORT_MAX_COLUMNS
    if hasattr(batch.original_file, "seek"):
        batch.original_file.seek(0)
    if suffix == ".csv":
        raw = batch.original_file.read()
        if isinstance(raw, str):
            text = raw
        else:
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                raise ValidationError("El archivo CSV debe usar codificación UTF-8.") from exc
        try:
            reader = csv.DictReader(io.StringIO(text))
            headers = reader.fieldnames or []
            if len(headers) > max_columns:
                raise ValidationError(f"El archivo supera el máximo permitido de {max_columns} columnas.")
            result = []
            for row_number, row in enumerate(reader, start=1):
                if row_number > max_rows:
                    raise ValidationError(f"El archivo supera el máximo permitido de {max_rows} filas de datos.")
                if None in row:
                    raise ValidationError(
                        f"La fila {row_number + 1} contiene más columnas que el encabezado declarado."
                    )
                result.append(_normalize_row(row))
            return result
        except csv.Error as exc:
            raise ValidationError("El archivo CSV no tiene una estructura válida.") from exc
    if suffix == ".xlsx":
        try:
            workbook = load_workbook(batch.original_file, read_only=True, data_only=True, keep_links=False)
            try:
                sheet = workbook.active
                if sheet.max_column > max_columns:
                    raise ValidationError(f"El archivo supera el máximo permitido de {max_columns} columnas.")
                if sheet.max_row > max_rows + 1:
                    raise ValidationError(f"El archivo supera el máximo permitido de {max_rows} filas de datos.")
                rows = iter(sheet.iter_rows(values_only=True))
                first_row = next(rows, None)
                if first_row is None:
                    return []
                headers = [normalize_key(cell) for cell in first_row]
                result = []
                for row_number, values in enumerate(rows, start=1):
                    if row_number > max_rows:
                        raise ValidationError(f"El archivo supera el máximo permitido de {max_rows} filas de datos.")
                    if not any(clean_cell(value) for value in values):
                        continue
                    row = {
                        headers[index]: clean_cell(value)
                        for index, value in enumerate(values)
                        if index < len(headers) and headers[index]
                    }
                    result.append(row)
                return result
            finally:
                workbook.close()
        except ValidationError:
            raise
        except Exception as exc:  # noqa: BLE001 - ES/EN: parser failures become input validation errors
            raise ValidationError("El archivo Excel .xlsx no tiene una estructura válida.") from exc
    raise ValidationError("Solo se permiten archivos CSV o Excel .xlsx para importaciones masivas.")


def _normalize_row(row: dict[str, Any]) -> dict[str, str]:
    return {normalize_key(key): clean_cell(value) for key, value in row.items() if normalize_key(key)}


def _find_branch(payload: dict[str, str], default_branch: Branch | None = None) -> Branch | None:
    code = payload.get("branch_code", "")
    name = payload.get("branch", "")
    qs = Branch.objects.filter(is_active=True)
    if code:
        branch = qs.filter(code__iexact=code).first()
        if branch:
            return branch
    if name:
        branch = qs.filter(name__iexact=name).first()
        if branch:
            return branch
    return default_branch


def _vehicle_part_specs_from_payload(payload: dict[str, str]) -> dict[str, dict[str, str]]:
    mapping = {
        "engine": VehiclePartSpecification.PartCode.ENGINE,
        "transmission": VehiclePartSpecification.PartCode.TRANSMISSION,
        "safety": VehiclePartSpecification.PartCode.SAFETY,
        "interior": VehiclePartSpecification.PartCode.INTERIOR,
        "technology": VehiclePartSpecification.PartCode.TECHNOLOGY,
        "suspension": VehiclePartSpecification.PartCode.SUSPENSION,
        "exterior": VehiclePartSpecification.PartCode.EXTERIOR,
        "cargo": VehiclePartSpecification.PartCode.CARGO,
        "capacity": VehiclePartSpecification.PartCode.CARGO,
    }
    result: dict[str, dict[str, str]] = {}
    for key, part_code in mapping.items():
        value = payload.get(key, "")
        if value:
            result[part_code] = {"title": dict(VehiclePartSpecification.PartCode.choices).get(part_code, key.title()), "description": value}
    return result


def _vehicle_highlights_from_payload(payload: dict[str, str]) -> list[dict[str, str]]:
    candidates = [
        ("Garantía", payload.get("warranty", "")),
        ("Consumo", payload.get("consumption", "")),
        ("Capacidad", payload.get("capacity", "")),
        ("Etiquetas", payload.get("tags", "")),
    ]
    return [{"title": title, "value": value} for title, value in candidates if value]


def _normalize_vehicle(payload: dict[str, str], *, batch: ImportBatch | None = None) -> tuple[dict[str, Any], list[str]]:
    errors = []
    brand = payload.get("brand", "")
    model = payload.get("model", "")
    vin = payload.get("vin", "").strip().upper() or None
    internal_code = payload.get("internal_code", "").strip().upper()
    year = None
    if not brand:
        errors.append("La marca es obligatoria.")
    if not model:
        errors.append("El modelo es obligatorio.")
    _collect_validation(errors, validate_no_unsafe_control_characters, brand)
    _collect_validation(errors, validate_no_unsafe_control_characters, model)
    _collect_validation(errors, validate_vehicle_identifier, vin)
    _collect_validation(errors, validate_vehicle_plate, payload.get("plate", ""))
    if vin and len(vin) > 40:
        errors.append("El VIN no puede superar 40 caracteres.")
    elif vin and Vehicle.objects.filter(vin__iexact=vin, is_deleted=True).exists():
        errors.append("El VIN pertenece a un vehículo eliminado. Debe restaurarse o revisarse manualmente antes de importar.")
    if internal_code and len(internal_code) > 80:
        errors.append("El código interno no puede superar 80 caracteres.")
    elif internal_code and Vehicle.objects.filter(internal_code__iexact=internal_code, is_deleted=True).exists():
        errors.append("El código interno pertenece a un vehículo eliminado. Debe restaurarse o revisarse manualmente.")
    elif internal_code and not Vehicle.objects.filter(internal_code__iexact=internal_code, is_deleted=False).exists():
        errors.append("El código interno indicado no existe. Para un vehículo nuevo déjalo vacío y Vinova Pro lo generará automáticamente.")
    if len(brand) > 120:
        errors.append("La marca no puede superar 120 caracteres.")
    if len(model) > 120:
        errors.append("El modelo no puede superar 120 caracteres.")
    try:
        year = to_int(payload.get("year"))
        if not year:
            errors.append("El año es obligatorio.")
        else:
            _collect_validation(errors, validate_vehicle_year, year)
    except ValidationError as exc:
        errors.append(str(exc))
    try:
        price = to_decimal(payload.get("price"), None)
        _collect_validation(errors, validate_nonnegative_decimal, price)
    except ValidationError as exc:
        price = None
        errors.append(str(exc))
    try:
        mileage = to_int(payload.get("mileage"), 0) or 0
        if mileage < 0:
            errors.append("El kilometraje no puede ser negativo.")
    except ValidationError as exc:
        mileage = 0
        errors.append(str(exc))
    for field_name in (
        "version",
        "color",
        "short_description",
        "description",
        "engine",
        "transmission",
        "safety",
        "interior",
        "technology",
        "suspension",
        "exterior",
        "cargo",
        "capacity",
        "warranty",
        "consumption",
        "tags",
    ):
        _collect_validation(errors, validate_no_unsafe_control_characters, payload.get(field_name, ""))
    default_branch = getattr(batch, "default_branch", None)
    branch = _find_branch(payload, default_branch=default_branch)
    branch_was_requested = bool(payload.get("branch") or payload.get("branch_code"))
    if branch_was_requested and not branch:
        errors.append("No se encontró la sucursal indicada.")
    if getattr(batch, "require_vehicle_branch", False) and not branch:
        errors.append("La sucursal es obligatoria para esta importación de vehículos. Indícala por fila o selecciona una sucursal por defecto.")
    status_raw = payload.get("status", "disponible").lower()
    status = VEHICLE_STATUS_MAP.get(status_raw)
    if status is None:
        status = Vehicle.Status.AVAILABLE
        errors.append("Estado no reconocido. Usa Disponible, Reservado, Vendido, En mantenimiento, Oculto o Archivado.")
    try:
        publish_catalog = to_bool_strict(
            payload.get("publish_catalog"),
            default=status == Vehicle.Status.AVAILABLE,
            field_label="Publicar en catálogo",
        )
    except ValidationError as exc:
        publish_catalog = False
        errors.append(str(exc))
    try:
        is_featured = to_bool_strict(
            payload.get("is_featured"),
            default=False,
            field_label="Destacado",
        )
    except ValidationError as exc:
        is_featured = False
        errors.append(str(exc))
    if publish_catalog and status != Vehicle.Status.AVAILABLE:
        errors.append("Solo los vehículos con estado Disponible pueden publicarse en el catálogo.")
    if publish_catalog and not payload.get("status"):
        status = Vehicle.Status.AVAILABLE
    normalized = {
        "brand": brand,
        "model": model,
        "year": year,
        "version": payload.get("version", ""),
        "internal_code": internal_code,
        "vin": vin,
        "plate": payload.get("plate", "").upper(),
        "color": payload.get("color", ""),
        "mileage": mileage,
        "price": str(price) if price is not None else None,
        "status": status,
        "branch_id": branch.pk if branch else None,
        "branch_source": "archivo" if branch_was_requested else ("sucursal_por_defecto" if branch else "sin_sucursal"),
        "short_description": payload.get("short_description", ""),
        "description": payload.get("description", ""),
        "is_featured": is_featured,
        "publish_catalog": publish_catalog,
        "part_specs": _vehicle_part_specs_from_payload(payload),
        "highlights": _vehicle_highlights_from_payload(payload),
    }
    return normalized, errors


def _normalize_customer(payload: dict[str, str], *, batch: ImportBatch | None = None) -> tuple[dict[str, Any], list[str]]:
    errors = []
    customer_type = CUSTOMER_TYPE_MAP.get(payload.get("customer_type", "natural").lower(), Customer.CustomerType.NATURAL)
    identification_type = IDENTIFICATION_MAP.get(payload.get("identification_type", "").lower(), "")
    status = CUSTOMER_STATUS_MAP.get(payload.get("status", "prospecto").lower(), Customer.Status.PROSPECT)
    identification_number = payload.get("identification_number", "")
    first_name = payload.get("first_name", "")
    last_name = payload.get("last_name", "")
    business_name = payload.get("business_name", "")
    if customer_type == Customer.CustomerType.COMPANY and not (business_name or identification_number):
        errors.append("Para empresa se requiere razón social o identificación.")
    if customer_type == Customer.CustomerType.NATURAL and not (first_name or last_name or identification_number):
        errors.append("Para persona natural se requiere nombre/apellido o identificación.")
    _collect_validation(errors, validate_human_name, first_name)
    _collect_validation(errors, validate_human_name, last_name)
    _collect_validation(errors, validate_phone_number, payload.get("phone", ""))
    _collect_validation(errors, validate_phone_number, payload.get("whatsapp", ""))
    _collect_validation(errors, validate_human_name, payload.get("city", ""))
    _collect_validation(errors, validate_human_name, payload.get("province", ""))
    for field_name in ("business_name", "address", "source"):
        _collect_validation(errors, validate_no_unsafe_control_characters, payload.get(field_name, ""))
    if payload.get("email"):
        _collect_validation(errors, validate_email, payload["email"])
    try:
        validate_identification_value(identification_type, identification_number)
    except ValidationError as exc:
        errors.extend(exc.messages)
    normalized = {
        "customer_type": customer_type,
        "identification_type": identification_type,
        "identification_number": identification_number or None,
        "first_name": first_name,
        "last_name": last_name,
        "business_name": business_name,
        "email": payload.get("email", ""),
        "phone": payload.get("phone", ""),
        "whatsapp": payload.get("whatsapp", ""),
        "address": payload.get("address", ""),
        "city": payload.get("city", ""),
        "province": payload.get("province", ""),
        "source": payload.get("source", "importacion"),
        "status": status,
    }
    return normalized, errors


def _normalize_inventory(payload: dict[str, str], *, batch: ImportBatch | None = None) -> tuple[dict[str, Any], list[str]]:
    errors = []
    sku = payload.get("sku", "").upper()
    name = payload.get("name", "") or payload.get("first_name", "")
    if not sku:
        errors.append("El SKU es obligatorio.")
    if not name:
        errors.append("El nombre del artículo es obligatorio.")
    for field_name, value in (
        ("sku", sku),
        ("name", name),
        ("category", payload.get("category", "")),
        ("description", payload.get("description", "")),
        ("unit", payload.get("unit", "unidad")),
    ):
        _collect_validation(errors, validate_no_unsafe_control_characters, value)
    try:
        price = to_decimal(payload.get("price"), Decimal("0.00")) or Decimal("0.00")
        cost = to_decimal(payload.get("cost"), None)
        _collect_validation(errors, validate_nonnegative_decimal, price)
        _collect_validation(errors, validate_nonnegative_decimal, cost)
    except ValidationError as exc:
        price, cost = Decimal("0.00"), None
        errors.append(str(exc))
    item_type = ITEM_TYPE_MAP.get(payload.get("item_type", "repuesto").lower(), InventoryItem.ItemType.SPARE_PART)
    status = ITEM_STATUS_MAP.get(payload.get("status", "activo").lower(), InventoryItem.Status.ACTIVE)
    normalized = {
        "sku": sku,
        "name": name,
        "category": payload.get("category", ""),
        "item_type": item_type,
        "description": payload.get("description", ""),
        "unit": payload.get("unit", "unidad") or "unidad",
        "price": str(price),
        "cost": str(cost) if cost is not None else None,
        "status": status,
        "is_public": to_bool(payload.get("is_public"), False),
        "track_stock": to_bool(payload.get("track_stock"), True),
    }
    return normalized, errors


def _normalize_stock(payload: dict[str, str], *, batch: ImportBatch | None = None) -> tuple[dict[str, Any], list[str]]:
    errors = []
    sku = payload.get("sku", "").upper()
    branch = _find_branch(payload, default_branch=getattr(batch, "default_branch", None))
    if not sku:
        errors.append("El SKU es obligatorio.")
    if not branch:
        errors.append("La sucursal es obligatoria y debe existir.")
    if sku and not InventoryItem.objects.filter(sku__iexact=sku).exists():
        errors.append("No existe un artículo con ese SKU.")
    try:
        quantity = to_decimal(payload.get("quantity"), None)
        if quantity is None or quantity < 0:
            errors.append("La cantidad debe ser mayor o igual a cero.")
    except ValidationError as exc:
        quantity = Decimal("0.00")
        errors.append(str(exc))
    try:
        minimum_stock = to_decimal(payload.get("minimum_stock"), Decimal("0.00")) or Decimal("0.00")
        _collect_validation(errors, validate_nonnegative_decimal, minimum_stock)
    except ValidationError as exc:
        minimum_stock = Decimal("0.00")
        errors.append(str(exc))
    normalized = {
        "sku": sku,
        "branch_id": branch.pk if branch else None,
        "quantity": str(quantity or Decimal("0.00")),
        "minimum_stock": str(minimum_stock),
        "location_code": payload.get("location_code", ""),
        "reference": payload.get("reference", "Importación masiva"),
    }
    _collect_validation(errors, validate_no_unsafe_control_characters, normalized["location_code"])
    _collect_validation(errors, validate_no_unsafe_control_characters, normalized["reference"])
    return normalized, errors


NORMALIZERS = {
    ImportBatch.ImportType.VEHICLES: _normalize_vehicle,
    ImportBatch.ImportType.CUSTOMERS: _normalize_customer,
    ImportBatch.ImportType.INVENTORY: _normalize_inventory,
    ImportBatch.ImportType.STOCK: _normalize_stock,
}
