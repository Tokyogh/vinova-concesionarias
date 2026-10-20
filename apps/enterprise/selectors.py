"""ES: Este módulo implementa consultas de lectura conscientes de autorización para el dominio de configuración empresarial.

EN: This module implements authorization-aware read queries for the enterprise domain.

Contexto existente / Existing context:
Read queries and authorization-aware selectors for the enterprise domain.
"""

from __future__ import annotations

from django.db.models import Count

from apps.companies.models import Company
from apps.enterprise.models import ApprovalPolicy, CompanyPublicSettings


def get_primary_company():
    return Company.objects.filter(is_active=True).order_by("id").first() or Company.objects.order_by("id").first()


def get_public_settings(company):
    settings, _ = CompanyPublicSettings.objects.get_or_create(company=company)
    return settings


def get_enterprise_overview():
    company = get_primary_company()
    if not company:
        return {"company": None, "public_settings": None, "sri_configuration": None, "approval_policies": []}
    public_settings = get_public_settings(company)
    sri_config = getattr(company, "sri_configuration", None)
    policies = ApprovalPolicy.objects.filter(company=company).prefetch_related("applies_to_roles").annotate(role_count=Count("applies_to_roles"))
    return {"company": company, "public_settings": public_settings, "sri_configuration": sri_config, "approval_policies": policies}


def approval_policy_queryset(company):
    return ApprovalPolicy.objects.filter(company=company).prefetch_related("applies_to_roles").order_by("action")
