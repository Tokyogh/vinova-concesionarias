"""ES: Este módulo implementa consultas de lectura conscientes de autorización para el dominio de calidad.

EN: This module implements authorization-aware read queries for the quality domain.

Contexto existente / Existing context:
Read queries and authorization-aware selectors for the quality domain.
"""

from __future__ import annotations

from django.db.models import Count, QuerySet

from apps.quality.models import QualityRun


def quality_run_queryset() -> QuerySet[QualityRun]:
    return (
        QualityRun.objects.select_related("requested_by")
        .annotate(check_count=Count("checks"))
        .order_by("-created_at")
    )


def recent_quality_runs(limit: int = 20):
    return quality_run_queryset()[:limit]
