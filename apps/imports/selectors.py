"""ES: Este módulo implementa consultas de lectura conscientes de autorización para el dominio de importaciones.

EN: This module implements authorization-aware read queries for the imports domain.

Contexto existente / Existing context:
Read queries and authorization-aware selectors for the imports domain.
"""

from __future__ import annotations

from django.db.models import Count, Q, Sum

from apps.accounts.scopes import accessible_branch_ids, users_in_branches_queryset
from apps.imports.models import ImportBatch

IMPORTS_PERMISSIONS = ("imports.manage",)


def _scoped_import_batches(queryset, *, user):
    """Deny-by-default: un lote solo es visible dentro del alcance de sucursal.

    Un lote sin sucursal por defecto se asocia a la sucursal del usuario que lo
    subió, de modo que la trazabilidad no se pierde pero tampoco cruza sucursales.
    """
    if user is None or not getattr(user, "is_authenticated", False):
        return queryset.none()
    if user.is_superuser:
        return queryset
    branch_ids = accessible_branch_ids(user, permission_codes=IMPORTS_PERMISSIONS)
    if branch_ids is None:
        return queryset
    if not branch_ids:
        return queryset.none()
    scoped_uploaders = users_in_branches_queryset(branch_ids).values("pk")
    return queryset.filter(
        Q(default_branch_id__in=branch_ids) | Q(default_branch__isnull=True, uploaded_by_id__in=scoped_uploaders)
    )


def import_batch_queryset(*, user=None):
    qs = ImportBatch.objects.select_related("uploaded_by", "confirmed_by", "default_branch").all()
    return _scoped_import_batches(qs, user=user)


def filter_import_batches(form, *, user=None):
    qs = import_batch_queryset(user=user)
    if form.is_valid():
        import_type = form.cleaned_data.get("import_type")
        status = form.cleaned_data.get("status")
        q = form.cleaned_data.get("q")
        if import_type:
            qs = qs.filter(import_type=import_type)
        if status:
            qs = qs.filter(status=status)
        if q:
            qs = qs.filter(Q(original_filename__icontains=q) | Q(file_hash__icontains=q) | Q(uploaded_by__username__icontains=q) | Q(uploaded_by__email__icontains=q))
    return qs


def imports_dashboard_context(*, user=None):
    qs = import_batch_queryset(user=user)
    return {
        "total_batches": qs.count(),
        "completed_batches": qs.filter(status=ImportBatch.Status.COMPLETED).count(),
        "failed_batches": qs.filter(status=ImportBatch.Status.FAILED).count(),
        "rows_processed": qs.aggregate(total=Sum("total_rows"))["total"] or 0,
        "recent_batches": qs.select_related("uploaded_by", "default_branch")[:8],
        "by_type": qs.values("import_type").annotate(count=Count("id")).order_by("import_type"),
    }
