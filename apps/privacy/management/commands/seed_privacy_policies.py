"""ES: Implementa el comando administrativo «seed privacy policies» para privacidad.

EN: Implements the «seed privacy policies» management command for privacy.

Contexto existente / Existing context:
Django management command for seed privacy policies.
"""

from django.core.management.base import BaseCommand

from apps.privacy.models import RetentionPolicy


POLICIES = [
    ("customers", "Perfiles de clientes", "customers", 1825, "review", "Revisar perfiles inactivos; no eliminar transacciones o documentos con obligación de conservación."),
    ("leads", "Leads y prospectos", "leads", 730, "anonymize", "Anonimizar prospectos inactivos cuando no exista relación contractual ni retención aplicable."),
    ("private-documents", "Documentos privados", "documents", 2555, "review", "Revisión legal obligatoria antes de archivar o eliminar archivos."),
    ("audit", "Auditoría y seguridad", "audit", 2555, "archive", "Conservar evidencias de seguridad y trazabilidad en almacenamiento protegido."),
    ("backups", "Copias de seguridad", "backups", 30, "delete", "Rotar backups locales únicamente después de comprobar la copia externa y un restore válido."),
]


class Command(BaseCommand):
    help = "Crea políticas base de retención y protección de datos."

    def handle(self, *args, **options):
        for code, name, category, days, action, description in POLICIES:
            RetentionPolicy.objects.update_or_create(code=code, defaults={"name": name, "data_category": category, "retention_days": days, "action": action, "description": description, "requires_legal_review": True})
        self.stdout.write(self.style.SUCCESS("Políticas de privacidad y retención creadas."))
