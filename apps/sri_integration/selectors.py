"""ES: Este módulo implementa consultas de lectura conscientes de autorización para el dominio de configuración SRI heredada.

EN: This module implements authorization-aware read queries for the sri integration domain.

Contexto existente / Existing context:
Read queries and authorization-aware selectors for the sri integration domain.
"""

from __future__ import annotations

from apps.sri_integration.models import SriConfiguration, SriEstablishment, SriSequence


def _initial_ruc(company) -> str:
    ruc = (company.ruc or "").strip()
    return ruc if len(ruc) == 13 and ruc.isdigit() else ""


def get_or_create_sri_configuration(company):
    config, _ = SriConfiguration.objects.get_or_create(
        company=company,
        defaults={
            "ruc": _initial_ruc(company),
            "legal_name": company.legal_name,
            "commercial_name": company.commercial_name,
            "matrix_address": company.address,
        },
    )
    return config


def sri_establishment_queryset(configuration):
    return SriEstablishment.objects.filter(configuration=configuration).select_related("branch")


def sri_sequence_queryset(configuration):
    return SriSequence.objects.filter(establishment__configuration=configuration).select_related("establishment")
