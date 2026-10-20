"""ES: Este módulo implementa el componente search para el dominio de infraestructura compartida.

EN: This module implements the search component for the common domain.

Contexto existente / Existing context:
Search support for the common domain.
"""

from __future__ import annotations

import re

from django.db.models import Q

from apps.common.normalization import identification_digits, normalize_phone


SEARCH_MIN_LENGTH = 2
SEARCH_MAX_LENGTH = 80
IDENTIFICATION_MIN_DIGITS = 6
PHONE_MIN_DIGITS = 6
PLATE_MIN_LENGTH = 3
VIN_MIN_LENGTH = 6
NAME_MIN_LENGTH = 2


def clean_search_query(value: str | None, *, min_length: int = SEARCH_MIN_LENGTH, max_length: int = SEARCH_MAX_LENGTH) -> str:
    """Normaliza una consulta de texto libre y descarta consultas demasiado cortas o largas.

    Evita que un criterio vacío o de un solo carácter dispare consultas en masa.
    """
    text = re.sub(r"\s+", " ", (value or "").strip())
    if max_length and len(text) > max_length:
        text = text[:max_length].strip()
    if len(text) < min_length:
        return ""
    return text


def clean_name_query(value: str | None) -> str:
    return clean_search_query(value, min_length=NAME_MIN_LENGTH)


def clean_identification_query(value: str | None) -> str:
    digits = identification_digits(value)
    if len(digits) < IDENTIFICATION_MIN_DIGITS:
        return ""
    return digits


def clean_phone_query(value: str | None) -> str:
    digits = normalize_phone(value)
    if len(digits) < PHONE_MIN_DIGITS:
        return ""
    return digits


def normalize_plate(value: str | None) -> str:
    cleaned = re.sub(r"[^A-Z0-9]", "", (value or "").upper())
    return cleaned if len(cleaned) >= PLATE_MIN_LENGTH else ""


def normalize_vin(value: str | None) -> str:
    cleaned = re.sub(r"[^A-Z0-9]", "", (value or "").upper())
    return cleaned if len(cleaned) >= VIN_MIN_LENGTH else ""


def plate_startswith_q(value: str | None, *, field: str = "plate") -> Q:
    """Filtro de placa tolerante a separadores (p. ej. `ABC-1234` o `abc1234`).

    Compara en mayúsculas y permite cualquier carácter no alfanumérico entre
    los caracteres introducidos, de modo que una placa almacenada con guiones
    siga siendo encontrada sin depender del formato exacto de guardado.
    """
    cleaned = normalize_plate(value)
    if not cleaned:
        return Q()
    pattern = r"[^A-Z0-9]*".join(re.escape(char) for char in cleaned)
    return Q(**{f"{field}__iregex": rf"^{pattern}"})
