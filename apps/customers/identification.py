"""ES: Este módulo implementa el componente identification para el dominio de clientes.

EN: This module implements the identification component for the customers domain.

Contexto existente / Existing context:
Identification support for the customers domain.
"""

from __future__ import annotations

from difflib import SequenceMatcher

from django.core.exceptions import ValidationError

from apps.common.normalization import identification_digits, normalize_identification
from apps.common.validators import is_valid_ec_cedula, is_valid_ec_ruc

FUZZY_MIN_RATIO = 0.92
FUZZY_MIN_LENGTH = 6
FUZZY_SCAN_LIMIT = 5000


def normalized_identification(value) -> str:
    return normalize_identification(value)


def is_ec_identification(identification_type: str, value: str) -> bool:
    if identification_type == "cedula":
        return True
    if identification_type == "ruc":
        return True
    if identification_type in {"passport", "other"}:
        return False
    digits = identification_digits(value)
    return len(digits) in {10, 13}


def validate_identification_value(identification_type: str, value) -> None:
    """ES: Valida y normaliza «validate identification value» antes de permitir efectos en clientes. Además, rechaza estados o entradas inválidas.

    EN: Validates and normalizes «validate identification value» before allowing effects in customers. It also rejects invalid input or state.
    """

    cleaned = normalize_identification(value)
    if not cleaned:
        return
    digits = identification_digits(cleaned)
    if identification_type == "cedula" or (identification_type in {"", None} and len(digits) == 10 and digits.isdigit()):
        if not is_valid_ec_cedula(cleaned):
            raise ValidationError({"identification_number": "Ingresa una cédula ecuatoriana válida de 10 dígitos."})
    elif identification_type == "ruc" or (identification_type in {"", None} and len(digits) == 13 and digits.isdigit()):
        if not is_valid_ec_ruc(cleaned):
            raise ValidationError({"identification_number": "Ingresa un RUC ecuatoriano válido de 13 dígitos."})
    elif len(cleaned) > 30:
        raise ValidationError({"identification_number": "La identificación supera los 30 caracteres permitidos."})


def normalize_for_storage(identification_type: str, value) -> str:
    cleaned = normalize_identification(value)
    if identification_type in {"cedula", "ruc"} or is_ec_identification(identification_type, cleaned):
        return identification_digits(cleaned)
    return cleaned


def validate_customer_identification(customer) -> None:
    identification_type = customer.identification_type or ""
    value = customer.identification_number
    validate_identification_value(identification_type, value)
    normalized = normalize_for_storage(identification_type, value)
    customer.identification_number = normalized or None
    duplicate = find_exact_duplicate(normalized, exclude_pk=customer.pk)
    if duplicate is not None:
        raise ValidationError(
            {"identification_number": f"Ya existe un cliente con esta identificación: {duplicate.display_name}."}
        )


def find_exact_duplicate(value, *, exclude_pk=None):
    from apps.customers.models import Customer

    cleaned = normalize_identification(value)
    if not cleaned:
        return None
    candidates = {
        identification_digits(cleaned),
        cleaned,
    }
    qs = Customer.objects.filter(identification_number__in=candidates)
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs.first()


def find_fuzzy_candidates(value, *, exclude_pk=None, limit: int = 5) -> list:
    from apps.customers.models import Customer

    cleaned = normalize_identification(value)
    if len(cleaned) < FUZZY_MIN_LENGTH:
        return []
    exact = find_exact_duplicate(cleaned, exclude_pk=exclude_pk)
    if exact is not None:
        return []
    matches = []
    for customer in Customer.objects.filter(is_deleted=False).order_by("-created_at")[:FUZZY_SCAN_LIMIT]:
        if exclude_pk and customer.pk == exclude_pk:
            continue
        other = normalize_identification(customer.identification_number)
        if len(other) < FUZZY_MIN_LENGTH:
            continue
        ratio = SequenceMatcher(None, cleaned, other).ratio()
        if ratio >= FUZZY_MIN_RATIO:
            matches.append((customer, round(ratio, 3)))
            if len(matches) >= limit:
                break
    return matches


def normalize_identification_data(customer_model=None) -> dict:
    """Data migration helper: normaliza identification_number existentes sin destruir datos.

    Solo actualiza cuando la forma normalizada no colisiona con otro registro.
    """
    if customer_model is None:
        from apps.customers.models import Customer as customer_model  # noqa: N806

    updated = 0
    skipped = 0
    seen: set[str] = set()
    for customer in customer_model.objects.all().order_by("id"):
        raw = customer.identification_number or ""
        if not raw:
            continue
        normalized = normalize_identification(raw)
        digits = identification_digits(normalized)
        if customer.identification_type in {"cedula", "ruc"} and digits:
            normalized = digits
        if not normalized or normalized == raw:
            seen.add(raw)
            continue
        if normalized in seen:
            skipped += 1
            continue
        exists = customer_model.objects.filter(identification_number=normalized).exclude(pk=customer.pk).exists()
        if exists:
            skipped += 1
            seen.add(normalized)
            continue
        customer.identification_number = normalized
        customer.save(update_fields=["identification_number", "updated_at"])
        seen.add(normalized)
        updated += 1
    return {"updated": updated, "skipped": skipped}
