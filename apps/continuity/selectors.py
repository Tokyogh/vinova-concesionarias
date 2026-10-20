"""ES: Este módulo implementa consultas de lectura conscientes de autorización para el dominio de continuidad.

EN: This module implements authorization-aware read queries for the continuity domain.

Contexto existente / Existing context:
Read queries and authorization-aware selectors for the continuity domain.
"""

from apps.continuity.models import BackupRecord, RestoreDrill


def continuity_metrics():
    latest = BackupRecord.objects.order_by("-created_at").first()
    return {
        "total": BackupRecord.objects.count(),
        "queued": BackupRecord.objects.filter(status=BackupRecord.Status.PENDING).count(),
        "running": BackupRecord.objects.filter(status=BackupRecord.Status.RUNNING).count(),
        "completed": BackupRecord.objects.filter(
            status__in=[BackupRecord.Status.COMPLETED, BackupRecord.Status.VERIFIED]
        ).count(),
        "failed": BackupRecord.objects.filter(status=BackupRecord.Status.FAILED).count(),
        "verified": BackupRecord.objects.filter(status=BackupRecord.Status.VERIFIED).count(),
        "restore_passed": RestoreDrill.objects.filter(status=RestoreDrill.Status.PASSED).count(),
        "latest": latest,
    }
