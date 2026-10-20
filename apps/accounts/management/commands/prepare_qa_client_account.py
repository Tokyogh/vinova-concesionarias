"""ES: Implementa el comando administrativo «prepare qa client account» para cuentas.

EN: Implements the «prepare qa client account» management command for accounts.

Contexto existente / Existing context:
Django management command for prepare qa client account.
"""

from __future__ import annotations

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.models import User
from apps.accounts.qa_client_services import prepare_qa_client_account, validate_qa_client_account
from apps.accounts.qa_safety import assert_non_production_database


class Command(BaseCommand):
    help = (
        "Prepara un expediente para una cuenta cliente QA seleccionada por ID; "
        "no modifica contraseñas, roles ni expedientes candidatos."
    )

    def add_arguments(self, parser):
        parser.add_argument("--user-id", type=int, required=True, help="ID exacto de la cuenta cliente QA.")
        parser.add_argument("--actor-id", type=int, required=True, help="ID exacto del operador autorizado.")
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Aplica el cambio. Sin esta opción solo valida y muestra el alcance.",
        )

    def handle(self, *args, **options):
        assert_non_production_database()
        user = self._user(options["user_id"], label="cuenta QA")
        actor = self._user(options["actor_id"], label="operador")

        try:
            if not options["apply"]:
                linked = validate_qa_client_account(actor=actor, user=user)
                outcome = (
                    f"ya está vinculada al expediente activo #{linked.pk}"
                    if linked is not None
                    else "puede recibir un expediente QA nuevo"
                )
                self.stdout.write(
                    f"Validación previa: la cuenta #{user.pk} {outcome}. "
                    "No se modificaron datos; agrega --apply para ejecutar."
                )
                return
            result = prepare_qa_client_account(actor=actor, user=user)
        except ValidationError as exc:
            message = "; ".join(exc.messages) if hasattr(exc, "messages") else str(exc)
            raise CommandError(message) from exc

        if result.created:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Cuenta QA #{user.pk} vinculada al expediente #{result.customer.pk} mediante servicios auditados."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Sin cambios: la cuenta QA #{user.pk} ya tiene un expediente activo vinculado."
                )
            )

    @staticmethod
    def _user(pk: int, *, label: str) -> User:
        try:
            return User.objects.get(pk=pk)
        except User.DoesNotExist as exc:
            raise CommandError(f"No existe la {label} indicada.") from exc
