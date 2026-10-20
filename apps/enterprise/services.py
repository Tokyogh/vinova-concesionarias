"""ES: Este módulo implementa servicios de negocio y efectos transaccionales para el dominio de configuración empresarial.

EN: This module implements business services and transactional effects for the enterprise domain.

Contexto existente / Existing context:
Transactional business services for the enterprise domain.
"""

from __future__ import annotations

from django.db import transaction

from apps.audit.services import audit_log
from apps.enterprise.models import ApprovalPolicy, CompanyPublicSettings


DEFAULT_APPROVAL_POLICIES = {
    ApprovalPolicy.Action.PRICE_CHANGE: {"mode": ApprovalPolicy.Mode.REQUIRE_APPROVAL, "notes": "Cambio de precio de vehículo requiere control."},
    ApprovalPolicy.Action.DISCOUNT: {"mode": ApprovalPolicy.Mode.THRESHOLD, "threshold_percent": 10, "notes": "Descuentos normales pueden ser automáticos; descuentos altos requieren autorización."},
    ApprovalPolicy.Action.SALE_CONFIRMATION: {"mode": ApprovalPolicy.Mode.AUTOMATIC, "notes": "Venta normal no debe frenar la operación."},
    ApprovalPolicy.Action.INVOICE_VOID: {"mode": ApprovalPolicy.Mode.REQUIRE_APPROVAL, "notes": "Anular comprobantes debe registrar motivo y autorización."},
    ApprovalPolicy.Action.STOCK_ADJUSTMENT: {"mode": ApprovalPolicy.Mode.THRESHOLD, "threshold_amount": 10, "notes": "Ajustes bajos pueden ser operativos; ajustes fuertes deben revisarse."},
    ApprovalPolicy.Action.PERMANENT_DELETE: {"mode": ApprovalPolicy.Mode.REQUIRE_APPROVAL, "notes": "Eliminar permanentemente siempre debe estar controlado."},
    ApprovalPolicy.Action.CRITICAL_STATUS_CHANGE: {"mode": ApprovalPolicy.Mode.REQUIRE_APPROVAL, "notes": "Cambios críticos se controlan por trazabilidad."},
}


def ensure_public_settings(company):
    settings, _ = CompanyPublicSettings.objects.get_or_create(company=company)
    return settings


@transaction.atomic
def update_company_core(*, actor, company, form):
    before = {"legal_name": company.legal_name, "commercial_name": company.commercial_name, "ruc": company.ruc, "email": company.email, "phone": company.phone, "primary_color": company.primary_color, "secondary_color": company.secondary_color}
    company = form.save()
    after = {"legal_name": company.legal_name, "commercial_name": company.commercial_name, "ruc": company.ruc, "email": company.email, "phone": company.phone, "primary_color": company.primary_color, "secondary_color": company.secondary_color}
    audit_log(user=actor, action="enterprise.company_core.update", target=company, before=before, after=after)
    return company


@transaction.atomic
def update_public_settings(*, actor, settings, form, action):
    before = {field: getattr(settings, field) for field in form.fields.keys() if hasattr(settings, field)}
    settings = form.save()
    after = {field: getattr(settings, field) for field in form.fields.keys() if hasattr(settings, field)}
    audit_log(user=actor, action=action, target=settings, before=before, after=after)
    return settings


@transaction.atomic
def ensure_default_approval_policies(*, company, actor=None):
    created = []
    for action, defaults in DEFAULT_APPROVAL_POLICIES.items():
        policy, was_created = ApprovalPolicy.objects.get_or_create(company=company, action=action, defaults=defaults)
        if was_created:
            created.append(action)
    if created and actor:
        audit_log(user=actor, action="enterprise.approval_policies.seed", target=company, after={"created": created})
    return ApprovalPolicy.objects.filter(company=company).order_by("action")


@transaction.atomic
def update_approval_policy(*, actor, policy, form):
    before = {"mode": policy.mode, "threshold_amount": str(policy.threshold_amount), "threshold_percent": str(policy.threshold_percent), "is_active": policy.is_active}
    policy = form.save()
    after = {"mode": policy.mode, "threshold_amount": str(policy.threshold_amount), "threshold_percent": str(policy.threshold_percent), "is_active": policy.is_active}
    audit_log(user=actor, action="enterprise.approval_policy.update", target=policy, before=before, after=after)
    return policy
