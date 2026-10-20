"""ES: Este módulo implementa el componente context processors para el dominio de configuración empresarial.

EN: This module implements the context processors component for the enterprise domain.

Contexto existente / Existing context:
Template context providers for the enterprise domain.
"""

from __future__ import annotations

from apps.common.validators import safe_hex_color
from apps.enterprise.selectors import get_primary_company


def enterprise_public_context(request):
    company = get_primary_company()
    if not company:
        return {
            "vinova_brand_primary": "#006BC7",
            "vinova_brand_secondary": "#0057A8",
            "vinova_company": None,
            "vinova_public_settings": None,
        }
    settings = getattr(company, "public_settings", None)
    return {
        "vinova_brand_primary": safe_hex_color(company.primary_color, "#006BC7"),
        "vinova_brand_secondary": safe_hex_color(company.secondary_color, "#0057A8"),
        "vinova_company": company,
        "vinova_public_settings": settings,
    }
