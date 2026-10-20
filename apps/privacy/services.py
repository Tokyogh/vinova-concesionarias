"""ES: Este módulo implementa servicios de negocio y efectos transaccionales para el dominio de privacidad.

EN: This module implements business services and transactional effects for the privacy domain.

Contexto existente / Existing context:
Transactional business services for the privacy domain.
"""

from __future__ import annotations

import hashlib
import json
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.audit.services import audit_log
from apps.privacy.models import AnonymizationRecord, ConsentRecord, DataExportJob, DataSubjectRequest


def _json_default(value):
    if hasattr(value, "isoformat"):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return str(value)


def _hash_json(payload) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=_json_default).encode("utf-8")).hexdigest()


def hash_text(value: str) -> str:
    return hashlib.sha256((value or "").encode("utf-8")).hexdigest() if value else ""


def register_lead_consent(lead) -> ConsentRecord | None:
    if not lead.consent_data_processing:
        return None
    consent, _ = ConsentRecord.objects.get_or_create(
        lead=lead,
        purpose=ConsentRecord.Purpose.DATA_PROCESSING,
        defaults={
            "customer": lead.customer,
            "status": ConsentRecord.Status.GRANTED,
            "notice_version": settings.VINOVA_PRIVACY_NOTICE_VERSION,
            "lawful_basis": "consentimiento",
            "source": lead.source,
            "subject_name": lead.full_name,
            "subject_email": lead.email,
            "accepted_at": lead.consent_at or lead.created_at or timezone.now(),
            "ip_hash": lead.ip_hash,
            "evidence": {
                "lead_code": lead.code,
                "source_url": lead.source_url,
                "consent_flag": True,
                "notice_version": settings.VINOVA_PRIVACY_NOTICE_VERSION,
            },
        },
    )
    return consent


def create_subject_export(*, actor, request_obj: DataSubjectRequest) -> DataExportJob:
    if not request_obj.customer_id:
        raise ValueError("La solicitud debe estar relacionada con un cliente antes de exportar.")
    if request_obj.status not in {DataSubjectRequest.Status.VERIFIED, DataSubjectRequest.Status.IN_PROGRESS, DataSubjectRequest.Status.APPROVED}:
        raise ValueError("La identidad debe estar verificada antes de exportar datos.")
    job = DataExportJob.objects.create(request=request_obj, customer=request_obj.customer, generated_by=actor, status=DataExportJob.Status.PROCESSING)
    try:
        customer = request_obj.customer
        payload = {
            "generated_at": timezone.now(),
            "request_id": str(request_obj.public_id),
            "customer": {
                "id": customer.pk, "type": customer.customer_type, "identification_type": customer.identification_type,
                "identification_number": customer.identification_number, "first_name": customer.first_name,
                "last_name": customer.last_name, "business_name": customer.business_name, "email": customer.email,
                "phone": customer.phone, "whatsapp": customer.whatsapp, "address": customer.address,
                "city": customer.city, "province": customer.province, "source": customer.source, "status": customer.status,
                "created_at": customer.created_at,
            },
            "leads": list(customer.crm_leads.values(
                "code", "request_type", "status", "source", "full_name", "email", "phone", "whatsapp", "city",
                "province", "message", "consent_data_processing", "consent_at", "created_at",
            )),
            "sales": list(customer.sales.values("number", "kind", "status", "source", "subtotal", "tax_total", "total", "amount_paid", "balance_due", "created_at")),
            "invoices": list(customer.invoices.values("number", "invoice_type", "status", "subtotal", "tax_total", "total", "issued_at", "created_at")),
            "documents": list(customer.private_documents.values("title", "document_type", "status", "original_name", "file_hash", "created_at")),
            "consents": list(customer.consents.values("purpose", "status", "notice_version", "lawful_basis", "source", "accepted_at", "revoked_at")),
            "notes": list(customer.notes.values("note_type", "title", "body", "is_important", "created_at")),
            "vehicle_interests": list(customer.vehicle_interests.values("brand", "model_name", "year_from", "year_to", "budget_min", "budget_max", "status", "notes", "created_at")),
        }
        export_root = Path(settings.PRIVATE_STORAGE_ROOT) / "privacy" / "exports"
        export_root.mkdir(parents=True, exist_ok=True)
        filename = f"datos_cliente_{customer.pk}_{job.public_id.hex[:10]}.json"
        path = export_root / filename
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default), encoding="utf-8")
        job.file_path = str(path.relative_to(Path(settings.PRIVATE_STORAGE_ROOT)))
        job.filename = filename
        job.size_bytes = path.stat().st_size
        job.sha256 = hashlib.sha256(path.read_bytes()).hexdigest()
        job.status = DataExportJob.Status.COMPLETED
        job.completed_at = timezone.now()
        job.expires_at = timezone.now() + timedelta(days=7)
        job.save(update_fields=["file_path", "filename", "size_bytes", "sha256", "status", "completed_at", "expires_at", "updated_at"])
        audit_log(user=actor, action="privacy.export.completed", target=job, customer=customer, after={"sha256": job.sha256, "size_bytes": job.size_bytes}, is_sensitive=True)
        return job
    except Exception as exc:  # noqa: BLE001
        job.status = DataExportJob.Status.FAILED
        job.error_message = str(exc)[:5000]
        job.save(update_fields=["status", "error_message", "updated_at"])
        audit_log(user=actor, action="privacy.export.failed", target=job, customer=request_obj.customer, after={"error": job.error_message}, severity="high", result="failure", is_sensitive=True)
        raise


def export_file_path(job: DataExportJob) -> Path:
    path = (Path(settings.PRIVATE_STORAGE_ROOT) / job.file_path).resolve()
    root = Path(settings.PRIVATE_STORAGE_ROOT).resolve()
    if root not in path.parents:
        raise RuntimeError("Ruta de exportación inválida.")
    return path


@transaction.atomic
def update_request_status(*, actor, request_obj: DataSubjectRequest, status: str, resolution: str = "", legal_hold_reason: str = "") -> DataSubjectRequest:
    before = {"status": request_obj.status, "resolution": request_obj.resolution, "legal_hold_reason": request_obj.legal_hold_reason}
    request_obj.status = status
    request_obj.resolution = resolution
    request_obj.legal_hold_reason = legal_hold_reason
    if status == DataSubjectRequest.Status.VERIFIED and not request_obj.identity_verified_at:
        request_obj.identity_verified_at = timezone.now()
        request_obj.identity_verified_by = actor
    if status == DataSubjectRequest.Status.COMPLETED:
        request_obj.completed_at = timezone.now()
    request_obj.save()
    revoked_count = 0
    if status == DataSubjectRequest.Status.COMPLETED and request_obj.request_type == DataSubjectRequest.RequestType.CONSENT_REVOCATION:
        consents = ConsentRecord.objects.filter(status=ConsentRecord.Status.GRANTED)
        if request_obj.customer_id:
            consents = consents.filter(customer_id=request_obj.customer_id)
        elif request_obj.requester_email:
            consents = consents.filter(subject_email__iexact=request_obj.requester_email)
        else:
            consents = consents.none()
        revoked_count = consents.update(status=ConsentRecord.Status.REVOKED, revoked_at=timezone.now())
    audit_log(user=actor, action="privacy.request.status", target=request_obj, customer=request_obj.customer, before=before, after={"status": status, "resolution": resolution, "legal_hold_reason": legal_hold_reason, "consents_revoked": revoked_count}, is_sensitive=True)
    return request_obj


@transaction.atomic
def anonymize_customer(*, actor, request_obj: DataSubjectRequest, notes: str = "") -> AnonymizationRecord:
    if request_obj.request_type not in {DataSubjectRequest.RequestType.DELETION, DataSubjectRequest.RequestType.ANONYMIZATION}:
        raise ValueError("La solicitud no corresponde a eliminación o anonimización.")
    if request_obj.status != DataSubjectRequest.Status.APPROVED:
        raise ValueError("La solicitud debe estar aprobada antes de anonimizar.")
    if request_obj.legal_hold_reason.strip():
        raise ValueError("Existe una retención legal activa; no se puede anonimizar todavía.")
    if not request_obj.customer_id:
        raise ValueError("La solicitud no tiene un cliente relacionado.")

    customer = request_obj.customer
    personal_snapshot = {
        "identification_number": customer.identification_number, "first_name": customer.first_name,
        "last_name": customer.last_name, "business_name": customer.business_name, "email": customer.email,
        "phone": customer.phone, "whatsapp": customer.whatsapp, "address": customer.address,
        "city": customer.city, "province": customer.province, "internal_notes": customer.internal_notes,
    }
    before_hash = _hash_json(personal_snapshot)
    fields = list(personal_snapshot.keys())
    warnings = []
    if customer.sales.exists() or customer.invoices.exists():
        warnings.append("Se conservaron referencias transaccionales por trazabilidad; los datos identificativos del perfil fueron anonimizados.")
    if customer.private_documents.exists():
        warnings.append("Los archivos documentales no se eliminaron automáticamente; deben revisarse según retención legal y política documental.")

    customer.identification_number = None
    customer.first_name = "Cliente"
    customer.last_name = f"Anonimizado {customer.pk}"
    customer.business_name = f"Entidad anonimizada {customer.pk}" if customer.customer_type == customer.CustomerType.COMPANY else ""
    customer.email = ""
    customer.phone = ""
    customer.whatsapp = ""
    customer.address = ""
    customer.city = ""
    customer.province = ""
    customer.source = "anonymized"
    customer.internal_notes = "Datos personales anonimizados mediante solicitud aprobada."
    customer.assigned_advisor = None
    customer.status = customer.Status.ARCHIVED
    customer.save()

    customer.crm_leads.update(
        full_name="Contacto anonimizado", email="", phone="", whatsapp="", city="", province="", message="",
        internal_notes="", lost_reason="", source_url="", referrer="", utm_source="", utm_medium="", utm_campaign="",
        session_hash="", ip_hash="",
    )
    customer.notes.update(title="Nota anonimizada", body="Contenido eliminado por anonimización.")
    customer.vehicle_interests.update(notes="")

    record = AnonymizationRecord.objects.create(
        request=request_obj, customer_reference=f"customer:{customer.pk}", before_hash=before_hash,
        fields_anonymized=fields, warnings=warnings, performed_by=actor, notes=notes,
    )
    request_obj.status = DataSubjectRequest.Status.COMPLETED
    request_obj.completed_at = timezone.now()
    request_obj.resolution = "Perfil y relaciones comerciales no legales anonimizados. " + " ".join(warnings)
    request_obj.save(update_fields=["status", "completed_at", "resolution", "updated_at"])
    audit_log(user=actor, action="privacy.customer.anonymized", target=record, customer=customer, after={"customer_reference": record.customer_reference, "before_hash": before_hash, "fields": fields, "warnings": warnings}, severity="high", is_sensitive=True)
    return record
