"""ES: Implementa el comando administrativo «check seed idempotency» para calidad.

EN: Implements the «check seed idempotency» management command for quality.

Contexto existente / Existing context:
Django management command for check seed idempotency.
"""

from __future__ import annotations

import os

from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import PermissionCode, Role
from apps.api.models import APIScope
from apps.help_center.models import HelpArticle, HelpCategory, HelpChecklist


class Command(BaseCommand):
    help = "Ejecuta dos veces los seeds base y comprueba que no creen duplicados. Úsese solo en una base QA."

    def _snapshot(self):
        return {
            "roles": Role.objects.count(),
            "permissions": PermissionCode.objects.count(),
            "api_scopes": APIScope.objects.count(),
            "help_categories": HelpCategory.objects.count(),
            "help_articles": HelpArticle.objects.count(),
            "help_checklists": HelpChecklist.objects.count(),
        }

    def handle(self, *args, **options):
        if os.getenv("VINOVA_QA_ACTIVE", "").lower() not in {"1", "true", "yes"}:
            raise CommandError("Este comando solo puede ejecutarse dentro del runner QA aislado.")
        for command in ("seed_roles", "seed_api_scopes", "seed_help_center"):
            call_command(command, verbosity=0)
        first = self._snapshot()
        for command in ("seed_roles", "seed_api_scopes", "seed_help_center"):
            call_command(command, verbosity=0)
        second = self._snapshot()
        if first != second:
            raise CommandError(f"Los seeds no son idempotentes. Primera ejecución: {first}. Segunda: {second}.")
        self.stdout.write(self.style.SUCCESS(f"Seeds idempotentes: {second}"))
