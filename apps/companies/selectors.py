"""ES: Este módulo implementa consultas de lectura conscientes de autorización para el dominio de empresa.

EN: This module implements authorization-aware read queries for the companies domain.

Contexto existente / Existing context:
Read queries and authorization-aware selectors for the companies domain.
"""

from django.db.models import Q, Count
from apps.companies.models import Company


def company_list_queryset(query: str = ""):
    qs = Company.objects.annotate(branch_count=Count("branches")).order_by("commercial_name")
    if query:
        qs = qs.filter(Q(commercial_name__icontains=query) | Q(legal_name__icontains=query) | Q(ruc__icontains=query))
    return qs


def company_detail_queryset():
    return Company.objects.prefetch_related("branches").annotate(branch_count=Count("branches"))
