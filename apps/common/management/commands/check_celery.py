"""ES: Implementa el comando administrativo «check celery» para infraestructura compartida.

EN: Implements the «check celery» management command for common.

Contexto existente / Existing context:
Django management command for check celery.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from config import celery_app


CRITICAL_TASKS = {
    "apps.common.tasks.system_heartbeat",
    "apps.continuity.tasks.run_backup_task",
    "apps.continuity.tasks.schedule_policy_backups",
    "apps.api.tasks.deliver_webhook_task",
    "apps.quality.tasks.run_quality_profile_task",
    "apps.quality.tasks.schedule_automated_quality_run",
}


def normalize_registered_tasks(tasks: object) -> set[str]:
    """Return canonical task names from Celery inspect output.

    ``inspect registered`` may return plain names or names followed by task
    metadata, for example ``task.name [rate_limit=2/h]``. Depending on the
    Celery version/serializer it can also be represented as a mapping.
    """
    if isinstance(tasks, Mapping):
        values: Iterable[object] = tasks.keys()
    elif isinstance(tasks, Iterable) and not isinstance(tasks, (str, bytes)):
        values = tasks
    elif tasks:
        values = (tasks,)
    else:
        values = ()

    normalized: set[str] = set()
    for value in values:
        name = str(value).strip()
        if not name:
            continue
        # Celery appends annotations such as ``[rate_limit=2/h]`` after a
        # whitespace separator. The canonical task name never contains spaces.
        normalized.add(name.split(maxsplit=1)[0])
    return normalized


class Command(BaseCommand):
    """ES: Agrupa el componente «command» del dominio de infraestructura compartida y sus reglas relacionadas.

    EN: Groups the «command» component and its related rules in the common domain.
    """

    help = "Comprueba broker, workers activos y tareas críticas registradas."

    def add_arguments(self, parser):
        parser.add_argument("--timeout", type=float, default=5.0)

    def handle(self, *args, **options):
        """ES: Orquesta «check celery» con fallos controlados para infraestructura compartida.

        EN: Orchestrates «check celery» with controlled failures for common.
        """

        timeout = options["timeout"]
        try:
            with celery_app.connection_for_read() as connection:
                connection.ensure_connection(max_retries=1)
        except Exception as exc:  # noqa: BLE001
            raise CommandError(f"Broker no disponible ({exc.__class__.__name__}).") from exc

        inspector = celery_app.control.inspect(timeout=timeout)
        replies = inspector.ping() or {}
        if not replies:
            raise CommandError("No respondió ningún Celery Worker.")

        registered = inspector.registered() or {}
        registered_by_worker = {
            worker: normalize_registered_tasks(tasks)
            for worker, tasks in registered.items()
        }
        all_registered = set().union(*registered_by_worker.values()) if registered_by_worker else set()
        absent = sorted(CRITICAL_TASKS.difference(all_registered))
        if absent:
            raise CommandError(
                "Tareas críticas ausentes en todos los workers: "
                f"{absent}. Tareas registradas por worker: {registered_by_worker}"
            )

        if settings.VINOVA_QA_EXECUTION_ENABLED:
            active_queues = inspector.active_queues() or {}
            qa_workers = sorted(
                worker
                for worker, queues in active_queues.items()
                if any(queue.get("name") == settings.CELERY_QA_QUEUE for queue in (queues or []))
            )
            if not qa_workers:
                raise CommandError(
                    f"VINOVA_QA_EXECUTION_ENABLED=True, pero ningún Worker consume la cola {settings.CELERY_QA_QUEUE!r}."
                )

        self.stdout.write(
            self.style.SUCCESS(
                "Broker disponible. "
                f"Workers activos: {', '.join(sorted(replies))}. "
                f"Tareas críticas verificadas: {len(CRITICAL_TASKS)}."
            )
        )
