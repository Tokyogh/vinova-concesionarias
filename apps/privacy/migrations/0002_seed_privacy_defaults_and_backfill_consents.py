from django.db import migrations
from django.utils import timezone


POLICIES = [
    ("customers", "Perfiles de clientes", "customers", 1825, "review", "Revisar perfiles inactivos; no eliminar transacciones o documentos con obligación de conservación."),
    ("leads", "Leads y prospectos", "leads", 730, "anonymize", "Anonimizar prospectos inactivos cuando no exista relación contractual ni retención aplicable."),
    ("private-documents", "Documentos privados", "documents", 2555, "review", "Revisión legal obligatoria antes de archivar o eliminar archivos."),
    ("audit", "Auditoría y seguridad", "audit", 2555, "archive", "Conservar evidencias de seguridad y trazabilidad en almacenamiento protegido."),
    ("backups", "Copias de seguridad", "backups", 30, "delete", "Rotar backups locales únicamente después de comprobar la copia externa y un restore válido."),
]


def seed_and_backfill(apps, schema_editor):
    RetentionPolicy = apps.get_model("privacy", "RetentionPolicy")
    ConsentRecord = apps.get_model("privacy", "ConsentRecord")
    Lead = apps.get_model("leads", "Lead")

    for code, name, category, days, action, description in POLICIES:
        RetentionPolicy.objects.update_or_create(
            code=code,
            defaults={
                "name": name,
                "data_category": category,
                "retention_days": days,
                "action": action,
                "description": description,
                "requires_legal_review": True,
                "is_active": True,
            },
        )

    for lead in Lead.objects.filter(consent_data_processing=True).iterator():
        ConsentRecord.objects.get_or_create(
            lead_id=lead.pk,
            purpose="data_processing",
            defaults={
                "customer_id": lead.customer_id,
                "status": "granted",
                "notice_version": "privacy-v1",
                "lawful_basis": "consentimiento",
                "source": lead.source,
                "subject_name": lead.full_name,
                "subject_email": lead.email,
                "accepted_at": lead.consent_at or lead.created_at or timezone.now(),
                "ip_hash": lead.ip_hash,
                "evidence": {"lead_code": lead.code, "source_url": lead.source_url, "consent_flag": True, "backfilled": True},
            },
        )


class Migration(migrations.Migration):
    dependencies = [("privacy", "0001_initial")]
    operations = [migrations.RunPython(seed_and_backfill, migrations.RunPython.noop)]
