"""ES: Este módulo implementa consultas de lectura conscientes de autorización para el dominio de API e integraciones.

EN: This module implements authorization-aware read queries for the api domain.

Contexto existente / Existing context:
Read queries and authorization-aware selectors for the api domain.
"""

from __future__ import annotations

from collections.abc import Iterable

from django.db.models import QuerySet

from apps.accounts.scopes import accessible_branch_ids


def integration_branch_ids(user, permission_codes: Iterable[str] = ("integrations.view", "integrations.manage")) -> set[int] | None:
    """Return allowed branches, or ``None`` when the user has global scope."""
    branch_ids = accessible_branch_ids(user, permission_codes=permission_codes)
    return None if branch_ids is None else set(branch_ids)


def scope_integration_queryset(queryset: QuerySet, user, branch_lookup: str) -> QuerySet:
    branch_ids = integration_branch_ids(user)
    if branch_ids is None:
        return queryset
    return queryset.filter(**{f"{branch_lookup}__in": branch_ids})
