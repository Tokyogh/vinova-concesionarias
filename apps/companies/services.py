"""ES: Este módulo implementa servicios de negocio y efectos transaccionales para el dominio de empresa.

EN: This module implements business services and transactional effects for the companies domain.

Contexto existente / Existing context:
Transactional business services for the companies domain.
"""

from django.db import transaction
from apps.audit.services import audit_log


@transaction.atomic
def create_company(*, actor, form):
    company = form.save()
    audit_log(user=actor, action="companies.company.create", target=company, after={"ruc": company.ruc, "commercial_name": company.commercial_name})
    return company


@transaction.atomic
def update_company(*, actor, company, form):
    before = {
        "legal_name": company.legal_name,
        "commercial_name": company.commercial_name,
        "ruc": company.ruc,
        "is_active": company.is_active,
    }
    company = form.save()
    after = {
        "legal_name": company.legal_name,
        "commercial_name": company.commercial_name,
        "ruc": company.ruc,
        "is_active": company.is_active,
    }
    audit_log(user=actor, action="companies.company.update", target=company, before=before, after=after)
    return company
