"""ES: Este módulo implementa servicios de negocio y efectos transaccionales para el dominio de sucursales.

EN: This module implements business services and transactional effects for the branches domain.

Contexto existente / Existing context:
Servicios transaccionales y auditables del dominio de sedes.

Transactional and auditable business services for the branches domain.
"""

from django.db import transaction
from apps.audit.services import audit_log
from apps.branches.models import Branch


def _branch_audit_snapshot(branch):
    return {
        "company_id": branch.company_id,
        "name": branch.name,
        "code": branch.code,
        "branch_type": branch.branch_type,
        "city": branch.city,
        "province": branch.province,
        "address": branch.address,
        "phone": branch.phone,
        "email": branch.email,
        "description": branch.description,
        "opening_hours": branch.opening_hours,
        "services": branch.public_services,
        "photo": branch.photo.name if branch.photo else "",
        "website_url": branch.website_url,
        "latitude": str(branch.latitude) if branch.latitude is not None else None,
        "longitude": str(branch.longitude) if branch.longitude is not None else None,
        "is_active": branch.is_active,
        "is_public": branch.is_public,
    }


@transaction.atomic
def create_branch(*, actor, form):
    branch = form.save()
    audit_log(
        user=actor,
        action="branches.branch.create",
        target=branch,
        after=_branch_audit_snapshot(branch),
    )
    return branch


@transaction.atomic
def update_branch(*, actor, branch, form):
    # ModelForm.full_clean() mutates form.instance before this service runs. Read
    # and lock the persisted row so the audit "before" snapshot remains truthful.
    persisted = Branch.objects.select_for_update().get(pk=branch.pk)
    before = _branch_audit_snapshot(persisted)
    branch = form.save()
    after = _branch_audit_snapshot(branch)
    audit_log(user=actor, action="branches.branch.update", target=branch, before=before, after=after)
    return branch
