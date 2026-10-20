"""ES: Este módulo implementa servicios de negocio y efectos transaccionales para el dominio de configuración SRI heredada.

EN: This module implements business services and transactional effects for the sri integration domain.

Contexto existente / Existing context:
Transactional business services for the sri integration domain.
"""

from __future__ import annotations

from django.db import transaction

from apps.audit.services import audit_log
from apps.sri_integration.models import SriEstablishment


@transaction.atomic
def update_sri_configuration(*, actor, config, form):
    before = {"environment": config.environment, "status": config.status, "ruc": config.ruc, "certificate_configured": bool(config.certificate_file)}
    config = form.save()
    after = {"environment": config.environment, "status": config.status, "ruc": config.ruc, "certificate_configured": bool(config.certificate_file)}
    audit_log(user=actor, action="sri.configuration.update", target=config, before=before, after=after)
    return config


@transaction.atomic
def create_or_update_establishment(*, actor, configuration, form):
    establishment = form.save(commit=False)
    establishment.configuration = configuration
    before = None if establishment._state.adding else {"code": establishment.establishment_code, "point": establishment.emission_point_code, "is_active": establishment.is_active}
    establishment.save()
    form.save_m2m()
    if establishment.is_default:
        SriEstablishment.objects.filter(configuration=configuration).exclude(pk=establishment.pk).update(is_default=False)
    after = {"code": establishment.establishment_code, "point": establishment.emission_point_code, "is_active": establishment.is_active, "is_default": establishment.is_default}
    audit_log(user=actor, action="sri.establishment.save", target=establishment, before=before, after=after)
    return establishment


@transaction.atomic
def create_or_update_sequence(*, actor, form):
    sequence = form.save()
    audit_log(user=actor, action="sri.sequence.save", target=sequence, after={"document_type": sequence.document_type, "next": sequence.next_number_preview, "is_active": sequence.is_active})
    return sequence
