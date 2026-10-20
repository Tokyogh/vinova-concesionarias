"""ES: Este módulo implementa el componente normalization para el dominio de infraestructura compartida.

EN: This module implements the normalization component for the common domain.

Contexto existente / Existing context:
Normalization support for the common domain.
"""

from __future__ import annotations

import re


def normalize_email(value: str | None) -> str:
    return (value or "").strip().lower()


def normalize_phone(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def normalize_identification(value: str | None) -> str:
    cleaned = (value or "").strip()
    cleaned = re.sub(r"[\s.\-/_]+", "", cleaned)
    return cleaned


def identification_digits(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")
