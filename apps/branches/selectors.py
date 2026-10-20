"""ES: Este módulo implementa consultas de lectura conscientes de autorización para el dominio de sucursales.

EN: This module implements authorization-aware read queries for the branches domain.

Contexto existente / Existing context:
Read queries and authorization-aware selectors for the branches domain.
"""

from django.db.models import Q, Count
from apps.branches.models import Branch


PUBLIC_BRANCH_TYPES = (
    Branch.BranchType.AFFILIATED_INSTITUTION,
    Branch.BranchType.OFFICE,
    Branch.BranchType.DEALERSHIP,
    Branch.BranchType.SERVICE_CENTER,
)


def branch_list_queryset(query: str = "", branch_type: str = ""):
    qs = Branch.objects.select_related("company").annotate(
        user_count=Count("users", distinct=True),
        vehicle_count=Count("vehicles", distinct=True),
    ).order_by("company__commercial_name", "city", "name")
    if query:
        qs = qs.filter(
            Q(name__icontains=query)
            | Q(code__icontains=query)
            | Q(city__icontains=query)
            | Q(company__commercial_name__icontains=query)
            | Q(company__legal_name__icontains=query)
        )
    if branch_type:
        qs = qs.filter(branch_type=branch_type)
    return qs


def branch_detail_queryset():
    return Branch.objects.select_related("company").annotate(
        user_count=Count("users", distinct=True),
        vehicle_count=Count("vehicles", distinct=True),
    )


def public_institution_queryset():
    return (
        Branch.objects.filter(
            is_active=True,
            is_public=True,
            company__is_active=True,
            branch_type__in=PUBLIC_BRANCH_TYPES,
        )
        .select_related("company")
        .order_by("branch_type", "name", "pk")
    )
