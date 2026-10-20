"""ES: Implementa el comando administrativo «bootstrap staging admin» para cuentas.

EN: Implements the «bootstrap staging admin» management command for accounts.

Contexto existente / Existing context:
Django management command for bootstrap staging admin.
"""

from __future__ import annotations

import os
import sys

from django.contrib.auth.password_validation import validate_password
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from apps.accounts.models import Role, User, UserRole

ALLOWED_ENVIRONMENTS = {"local", "staging", "demo", "test"}


class Command(BaseCommand):
    """ES: Agrupa el componente «command» del dominio de cuentas y sus reglas relacionadas. Además, conserva atomicidad y bloqueos explícitos, rechaza estados o entradas inválidas.

    EN: Groups the «command» component and its related rules in the accounts domain. It also preserves atomicity and explicit locking, rejects invalid input or state.
    """

    help = "Crea o repara un administrador general para uso humano en local o staging."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--email", required=True)
        parser.add_argument("--password-stdin", action="store_true")
        parser.add_argument("--clear-login-cache", action="store_true")

    def handle(self, *args, **options):
        """ES: Orquesta «bootstrap staging admin» con fallos controlados para cuentas. Además, conserva atomicidad y bloqueos explícitos, rechaza estados o entradas inválidas.

        EN: Orchestrates «bootstrap staging admin» with controlled failures for accounts. It also preserves atomicity and explicit locking, rejects invalid input or state.
        """

        self._assert_safe_environment()
        username = options["username"].strip()
        email = options["email"].strip().lower()
        if not username or not email:
            raise CommandError("Usuario y correo son obligatorios.")
        if not options["password_stdin"]:
            raise CommandError("Use --password-stdin para no exponer la contraseña en la línea de comandos.")
        password = sys.stdin.readline().rstrip("\r\n")
        if not password:
            raise CommandError("No se recibió una contraseña por stdin.")

        call_command("seed_roles", verbosity=0)
        with transaction.atomic():
            matches = list(User.objects.filter(Q(username__iexact=username) | Q(email__iexact=email)).order_by("pk"))
            if len(matches) > 1:
                raise CommandError("El usuario y el correo pertenecen a cuentas diferentes; corríjalas desde Django admin.")
            user = matches[0] if matches else User(username=username, email=email)
            conflict = User.objects.exclude(pk=user.pk).filter(Q(username__iexact=username) | Q(email__iexact=email)).exists()
            if conflict:
                raise CommandError("El usuario o correo ya pertenece a otra cuenta.")

            user.username = username
            user.email = email
            user.is_active = True
            user.is_staff = True
            user.is_superuser = False
            user.must_change_password = False
            user.failed_login_count = 0
            user.locked_until = None
            try:
                validate_password(password, user=user)
            except ValidationError as exc:
                raise CommandError(" ".join(exc.messages)) from exc
            user.set_password(password)
            user.save()

            role = Role.objects.get(code="admin_general")
            assignments = UserRole.objects.filter(user=user, role=role, branch__isnull=True).order_by("pk")
            assignment = assignments.first()
            if assignment is None:
                assignment = UserRole.objects.create(user=user, role=role, branch=None, is_active=True)
            else:
                assignment.is_active = True
                assignment.starts_at = None
                assignment.expires_at = None
                assignment.save(update_fields=["is_active", "starts_at", "expires_at", "updated_at"])
                assignments.exclude(pk=assignment.pk).update(is_active=False)

        if options["clear_login_cache"]:
            cache.clear()
        self.stdout.write(self.style.SUCCESS(f"Administrador general listo: {user.username} ({user.email})"))

    @staticmethod
    def _assert_safe_environment():
        environment = os.getenv("VINOVA_ENVIRONMENT", "").strip().lower()
        if environment not in ALLOWED_ENVIRONMENTS:
            raise CommandError("Este comando solo se permite en local, staging, demo o test.")
