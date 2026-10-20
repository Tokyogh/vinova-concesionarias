"""ES: Este módulo implementa consultas de lectura conscientes de autorización para el dominio de documentos.

EN: This module implements authorization-aware read queries for the documents domain.

Contexto existente / Existing context:
Read queries and authorization-aware selectors for the documents domain.
"""

from __future__ import annotations

from django.db.models import Q, Sum

from apps.accounts.scopes import accessible_branch_ids
from apps.documents.models import DocumentCategory, PrivateDocument, ReusableAsset

DOCUMENT_SCOPE_PERMISSIONS = ("documents.view", "documents.manage", "documents.download_private")


def document_categories_queryset():
    return DocumentCategory.objects.filter(is_active=True).order_by("scope", "name")


def has_global_document_scope(user) -> bool:
    """Deny-by-default: sin usuario autenticado no hay alcance global de documentos.

    Delega en el alcance canónico de cuentas para que la vigencia de la
    asignación de rol (starts_at/expires_at) y la activación del rol también
    apliquen a la biblioteca documental.
    """
    return accessible_branch_ids(user, permission_codes=DOCUMENT_SCOPE_PERMISSIONS) is None


def allowed_document_branch_ids(user) -> set[int]:
    branch_ids = accessible_branch_ids(user, permission_codes=DOCUMENT_SCOPE_PERMISSIONS)
    if branch_ids is None:
        return set()
    return set(branch_ids)


def reusable_assets_queryset(*, query="", asset_type="", visibility="", user=None):
    qs = ReusableAsset.objects.filter(is_deleted=False).select_related(
        "branch", "uploaded_by", "vehicle_model", "vehicle_model__brand"
    )
    if user is not None and getattr(user, "is_authenticated", False) and not has_global_document_scope(user):
        branch_ids = allowed_document_branch_ids(user)
        # Los recursos públicos siguen disponibles; los internos requieren alcance de sucursal.
        scope_filter = Q(visibility=ReusableAsset.Visibility.PUBLIC)
        if branch_ids:
            scope_filter |= Q(branch_id__in=branch_ids)
        qs = qs.filter(scope_filter)
    if query:
        qs = qs.filter(Q(title__icontains=query) | Q(description__icontains=query) | Q(original_name__icontains=query) | Q(file_hash__icontains=query))
    if asset_type:
        qs = qs.filter(asset_type=asset_type)
    if visibility:
        qs = qs.filter(visibility=visibility)
    return qs.order_by("-created_at")


def private_documents_queryset(*, query="", document_type="", status="", branch=None, user=None, sort=""):
    qs = PrivateDocument.objects.filter(is_deleted=False).select_related("category", "branch", "customer", "vehicle", "sale", "uploaded_by")
    if user is not None and getattr(user, "is_authenticated", False) and not has_global_document_scope(user):
        branch_ids = allowed_document_branch_ids(user)
        qs = qs.filter(branch_id__in=branch_ids) if branch_ids else qs.none()
    if query:
        qs = qs.filter(
            Q(title__icontains=query)
            | Q(original_name__icontains=query)
            | Q(notes__icontains=query)
            | Q(customer__first_name__icontains=query)
            | Q(customer__last_name__icontains=query)
            | Q(customer__business_name__icontains=query)
            | Q(customer__identification_number__icontains=query)
            | Q(vehicle__internal_code__icontains=query)
            | Q(vehicle__vin__icontains=query)
            | Q(vehicle__plate__icontains=query)
            | Q(sale__number__icontains=query)
        )
    if document_type:
        qs = qs.filter(document_type=document_type)
    if status:
        qs = qs.filter(status=status)
    if branch:
        qs = qs.filter(branch=branch)
    ordering = {
        "oldest": ("created_at",), "title_asc": ("title", "-created_at"),
        "expires_asc": ("expires_at", "-created_at"),
    }.get(sort, ("-created_at",))
    return qs.order_by(*ordering)


def document_dashboard_metrics(*, user=None):
    private_qs = private_documents_queryset(user=user)
    asset_qs = reusable_assets_queryset(user=user)
    return {
        "private_documents": private_qs.count(),
        "confidential_documents": private_qs.filter(is_confidential=True).count(),
        "public_assets": asset_qs.filter(visibility=ReusableAsset.Visibility.PUBLIC, is_active=True).count(),
        "storage_bytes": (private_qs.aggregate(total=Sum("size_bytes"))["total"] or 0)
        + (asset_qs.aggregate(total=Sum("size_bytes"))["total"] or 0),
    }


def recent_documents(limit=8, *, user=None):
    return private_documents_queryset(user=user)[:limit]


def recent_assets(limit=8, *, user=None):
    return reusable_assets_queryset(user=user)[:limit]
