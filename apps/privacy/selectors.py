"""ES: Este módulo implementa consultas de lectura conscientes de autorización para el dominio de privacidad.

EN: This module implements authorization-aware read queries for the privacy domain.

Contexto existente / Existing context:
Read queries and authorization-aware selectors for the privacy domain.
"""

from django.db.models import Q
from django.utils import timezone

from apps.accounts.scopes import accessible_branch_ids
from apps.privacy.models import ConsentRecord, DataExportJob, DataSubjectRequest, RetentionPolicy


def scoped_consent_queryset(user, *, permission_code="privacy.view"):
    qs = ConsentRecord.objects.select_related("customer", "lead", "captured_by")
    branch_ids = accessible_branch_ids(user, permission_codes=(permission_code,))
    if branch_ids is None:
        return qs
    if not branch_ids:
        return qs.none()
    return qs.filter(
        Q(customer__assigned_branch_id__in=branch_ids)
        | Q(lead__branch_id__in=branch_ids)
        | Q(captured_by=user)
    ).distinct()


def scoped_data_request_queryset(user, *, permission_code="privacy.view"):
    qs = DataSubjectRequest.objects.select_related("customer", "assigned_to", "identity_verified_by")
    branch_ids = accessible_branch_ids(user, permission_codes=(permission_code,))
    if branch_ids is None:
        return qs
    if not branch_ids:
        return qs.none()
    return qs.filter(Q(customer__assigned_branch_id__in=branch_ids) | Q(assigned_to=user)).distinct()


def scoped_export_job_queryset(user, *, permission_code="privacy.view"):
    request_ids = scoped_data_request_queryset(user, permission_code=permission_code).values("pk")
    return DataExportJob.objects.filter(request_id__in=request_ids).select_related(
        "request",
        "customer",
        "generated_by",
    )


def scoped_retention_policy_queryset(user, *, permission_code="privacy.view"):
    branch_ids = accessible_branch_ids(user, permission_codes=(permission_code,))
    return RetentionPolicy.objects.all() if branch_ids is None else RetentionPolicy.objects.none()


def privacy_metrics(user):
    requests = scoped_data_request_queryset(user)
    consents = scoped_consent_queryset(user)
    exports = scoped_export_job_queryset(user)
    policies = scoped_retention_policy_queryset(user)
    closed_statuses = [
        DataSubjectRequest.Status.COMPLETED,
        DataSubjectRequest.Status.REJECTED,
        DataSubjectRequest.Status.CANCELLED,
    ]
    return {
        "requests_total": requests.count(),
        "requests_open": requests.exclude(status__in=closed_statuses).count(),
        "identity_pending": requests.filter(status=DataSubjectRequest.Status.IDENTITY_PENDING).count(),
        "overdue": requests.filter(due_at__lt=timezone.now()).exclude(status__in=closed_statuses).count(),
        "consents_active": consents.filter(status=ConsentRecord.Status.GRANTED).count(),
        "exports_active": exports.filter(
            status=DataExportJob.Status.COMPLETED,
            expires_at__gt=timezone.now(),
        ).count(),
        "retention_policies": policies.filter(is_active=True).count(),
    }
