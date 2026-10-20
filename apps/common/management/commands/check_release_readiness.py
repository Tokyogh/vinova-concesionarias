"""ES: Implementa el comando administrativo «check release readiness» para infraestructura compartida.

EN: Implements the «check release readiness» management command for common.

Contexto existente / Existing context:
Django management command for check release readiness.
"""

from __future__ import annotations

import json
from io import StringIO

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from apps.common.release_checks import ReleaseCheckResult, run_static_release_checks


class Command(BaseCommand):
    """ES: Agrupa el componente «command» del dominio de infraestructura compartida y sus reglas relacionadas.

    EN: Groups the «command» component and its related rules in the common domain.
    """

    help = "Comprueba rutas, assets, Celery, Docker, documentación y preparación estática del release."

    def add_arguments(self, parser):
        parser.add_argument("--database", action="store_true", help="Exige que todas las migraciones estén aplicadas.")
        parser.add_argument("--with-celery", action="store_true", help="Comprueba también broker y Workers activos.")
        parser.add_argument("--strict", action="store_true", help="Trata advertencias como errores.")
        parser.add_argument("--json", action="store_true", dest="as_json", help="Emite un resultado JSON.")

    def _database_check(self) -> ReleaseCheckResult:
        executor = MigrationExecutor(connection)
        plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
        if plan:
            labels = [f"{migration.app_label}.{migration.name}" for migration, _ in plan[:10]]
            suffix = "…" if len(plan) > 10 else ""
            return ReleaseCheckResult(
                code="database.migrations",
                level="error",
                message=f"Hay {len(plan)} migraciones pendientes: {', '.join(labels)}{suffix}",
            )
        return ReleaseCheckResult(
            code="database.migrations",
            level="ok",
            message="La base de datos no tiene migraciones pendientes.",
        )

    def handle(self, *args, **options):
        """ES: Orquesta «check release readiness» con fallos controlados para infraestructura compartida.

        EN: Orchestrates «check release readiness» with controlled failures for common.
        """

        output = StringIO()
        call_command("check", stdout=output, stderr=output)
        call_command("makemigrations", check=True, dry_run=True, verbosity=0, stdout=output, stderr=output)

        results = run_static_release_checks()
        if options["database"]:
            results.append(self._database_check())
        if options["with_celery"]:
            call_command("check_celery", stdout=output, stderr=output)
            results.append(
                ReleaseCheckResult(
                    code="celery.runtime",
                    level="ok",
                    message="Broker, Workers y tareas críticas respondieron correctamente.",
                )
            )

        has_error = any(item.level == "error" for item in results)
        has_warning = any(item.level == "warning" for item in results)
        failed = has_error or (options["strict"] and has_warning)

        if options["as_json"]:
            payload = {
                "status": "failed" if failed else "ok",
                "checks": [{"code": item.code, "level": item.level, "message": item.message} for item in results],
            }
            self.stdout.write(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            for item in results:
                prefix = {"ok": "OK", "warning": "WARN", "error": "ERROR"}[item.level]
                formatter = {
                    "ok": self.style.SUCCESS,
                    "warning": self.style.WARNING,
                    "error": self.style.ERROR,
                }[item.level]
                self.stdout.write(formatter(f"[{prefix}] {item.code}: {item.message}"))
            self.stdout.write(output.getvalue().strip())

        if failed:
            raise CommandError("La preparación del release tiene verificaciones fallidas.")
        self.stdout.write(self.style.SUCCESS(f"Release listo a nivel estático: {len(results)} verificaciones."))
