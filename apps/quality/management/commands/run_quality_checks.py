"""ES: Implementa el comando administrativo «run quality checks» para calidad.

EN: Implements the «run quality checks» management command for quality.

Contexto existente / Existing context:
Django management command for run quality checks.
"""

from __future__ import annotations

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.quality.models import QualityRun
from apps.quality.runner import VALID_PROFILES, run_quality_profile
from apps.quality.services import apply_quality_report, create_quality_run, mark_quality_run_error, mark_quality_run_running


class Command(BaseCommand):
    help = "Ejecuta un perfil del QA Bot y conserva su reporte privado e historial empresarial."

    def add_arguments(self, parser):
        parser.add_argument("--profile", choices=sorted(VALID_PROFILES), default="quick")
        parser.add_argument("--no-persist", action="store_true", help="Genera reportes sin registrar la ejecución en la BD.")
        parser.add_argument("--allow-sqlite", action="store_true", help="Permite release sin PostgreSQL aislado; solo diagnóstico local.")

    def handle(self, *args, **options):
        profile = options["profile"]
        run = None
        run_id = None
        if not options["no_persist"]:
            try:
                run = create_quality_run(profile=profile, trigger=QualityRun.Trigger.CLI, actor=None)
                run = mark_quality_run_running(run)
                run_id = str(run.public_id)
            except ValueError as exc:
                raise CommandError(str(exc)) from exc
        try:
            report = run_quality_profile(
                profile=profile,
                root=settings.BASE_DIR,
                report_dir=settings.VINOVA_QA_REPORT_ROOT,
                run_id=run_id,
                require_postgres=profile == QualityRun.Profile.RELEASE and not options["allow_sqlite"],
            )
            if run:
                apply_quality_report(run, report)
        except Exception as exc:
            if run:
                mark_quality_run_error(run, f"{exc.__class__.__name__}: {exc}")
            raise CommandError(str(exc)) from exc

        counts = report["counts"]
        self.stdout.write(
            f"QA {profile}: {report['status']} · aprobadas={counts['passed']} · "
            f"advertencias={counts['warning']} · fallidas={counts['failed']}"
        )
        self.stdout.write(f"JSON: {settings.VINOVA_QA_REPORT_ROOT / report['report_json_path']}")
        self.stdout.write(f"HTML: {settings.VINOVA_QA_REPORT_ROOT / report['report_html_path']}")
        if report["status"] != "passed":
            raise CommandError("La validación QA contiene controles fallidos.")
        self.stdout.write(self.style.SUCCESS("Validación QA aprobada."))
