"""ES: Este módulo expone tareas asíncronas y sus límites operativos para el dominio de reportes.

EN: This module exposes asynchronous tasks and their operational limits for the reports domain.

Contexto existente / Existing context:
Asynchronous task entry points for the reports domain.
"""

from __future__ import annotations

from celery import shared_task


@shared_task
def generate_report_export_task(export_job_id):
    """Punto de extensión para reportes pesados.

    v0.13 deja el contrato listo para ejecutar exportaciones en segundo plano.
    Las exportaciones livianas se generan desde la vista para mantener el flujo
    simple durante desarrollo local.
    """

    return {"export_job_id": export_job_id, "status": "pending_implementation"}
