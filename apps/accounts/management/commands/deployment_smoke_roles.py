"""ES: Implementa el comando administrativo «deployment smoke roles» para cuentas.

EN: Implements the «deployment smoke roles» management command for accounts.

Contexto existente / Existing context:
Django management command for deployment smoke roles.
"""

from __future__ import annotations

import hashlib
import json
import os
import secrets
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q
from django.utils import timezone

from apps.accounts.forms import BRANCH_REQUIRED_ROLE_CODES
from apps.accounts.management.commands.seed_roles import ROLE_DEFINITIONS
from apps.accounts.models import Role, User, UserRole
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.vehicles.models import VehicleBrand, VehicleModel

ALLOWED_ENVIRONMENTS = {"local", "staging", "demo", "test"}


class Command(BaseCommand):
    """Manage isolated temporary role accounts for deployment smoke tests."""

    help = "Crea, inspecciona o desactiva cuentas temporales para la matriz de roles del Deployment Smoke Bot."

    def add_arguments(self, parser):
        parser.add_argument("action", choices=["provision", "disable", "status"])
        parser.add_argument("--run-id", required=True)
        parser.add_argument("--output", type=Path)
        parser.add_argument("--expires-hours", type=int, default=4)

    def handle(self, *args, **options):
        self._assert_safe_environment()
        run_id = self._normalize_run_id(options["run_id"])
        action = options["action"]
        if action == "provision":
            manifest = self._provision(run_id, options["expires_hours"])
            output = options.get("output")
            if output:
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
                try:
                    os.chmod(output, 0o600)
                except OSError:
                    pass
                self.stdout.write(self.style.SUCCESS(f"Manifest creado: {output}"))
            else:
                self.stdout.write(json.dumps(manifest, ensure_ascii=False))
        elif action == "disable":
            count = self._disable(run_id)
            self.stdout.write(self.style.SUCCESS(f"Cuentas desactivadas: {count}"))
        else:
            rows = list(
                User.objects.filter(username__startswith=f"smoke.role.{run_id}.")
                .order_by("username")
                .values("username", "is_active", "branch__code")
            )
            self.stdout.write(json.dumps({"run_id": run_id, "accounts": rows}, ensure_ascii=False, indent=2))

    def _assert_safe_environment(self):
        environment = os.getenv("VINOVA_ENVIRONMENT", "").strip().lower()
        allowed = os.getenv("VINOVA_SMOKE_ALLOW_ROLE_PROVISION", "").strip().lower() in {"1", "true", "yes", "on"}
        if not allowed:
            raise CommandError("Requiere VINOVA_SMOKE_ALLOW_ROLE_PROVISION=true.")
        if environment not in ALLOWED_ENVIRONMENTS and not settings.DEBUG:
            raise CommandError("La creación automática de roles está prohibida fuera de local/staging/demo/test.")

    @staticmethod
    def _normalize_run_id(value: str) -> str:
        normalized = "".join(ch for ch in value.lower() if ch.isalnum())[:20]
        if len(normalized) < 6:
            raise CommandError("--run-id debe contener al menos 6 caracteres alfanuméricos.")
        return normalized

    @transaction.atomic
    def _provision(self, run_id: str, expires_hours: int) -> dict:
        if expires_hours < 1 or expires_hours > 24:
            raise CommandError("--expires-hours debe estar entre 1 y 24.")
        call_command("seed_roles", verbosity=0)
        company_email = f"smoke.roles.{run_id}@vinova.invalid"
        company, _ = Company.objects.update_or_create(
            email=company_email,
            defaults={
                "ruc": self._technical_ruc(run_id),
                "legal_name": f"SMOKE Role Matrix {run_id}",
                "commercial_name": f"SMOKE Roles {run_id}",
                "is_active": True,
            },
        )
        branches = []
        for suffix, city in (("a", "Quito"), ("b", "Guayaquil")):
            branch, _ = Branch.objects.update_or_create(
                company=company,
                code=f"smoke-{run_id}-{suffix}"[:60],
                defaults={
                    "name": f"SMOKE Sucursal {suffix.upper()} {run_id}",
                    "city": city,
                    "branch_type": Branch.BranchType.DEALERSHIP,
                    "is_public": False,
                    "is_active": True,
                },
            )
            branches.append(branch)

        brand, _ = VehicleBrand.objects.update_or_create(
            name=f"SMOKE-{run_id}"[:120],
            defaults={"is_active": True},
        )
        vehicle_model, _ = VehicleModel.objects.update_or_create(
            brand=brand,
            name=f"Modelo QA {run_id}"[:120],
            defaults={"segment": "QA", "is_active": True},
        )

        expires_at = timezone.now() + timedelta(hours=expires_hours)
        accounts = {}
        for role_code in ROLE_DEFINITIONS:
            role = Role.objects.get(code=role_code)
            password = f"Smk!{secrets.token_urlsafe(22)}aA9"
            username = f"smoke.role.{run_id}.{role_code}"[:150]
            branch = branches[0] if role_code in BRANCH_REQUIRED_ROLE_CODES else None
            user, _ = User.objects.update_or_create(
                username=username,
                defaults={
                    "email": f"{username}@vinova.invalid",
                    "first_name": "SMOKE",
                    "last_name": role_code,
                    "branch": branch,
                    "is_active": True,
                    "is_staff": role_code != "cliente",
                    "is_superuser": False,
                    "must_change_password": False,
                    "locked_until": None,
                    "failed_login_count": 0,
                },
            )
            user.set_password(password)
            user.save(update_fields=["password"])
            UserRole.objects.filter(user=user).exclude(role=role, branch=branch).update(is_active=False)
            assignment, _ = UserRole.objects.get_or_create(user=user, role=role, branch=branch)
            assignment.is_active = True
            assignment.expires_at = expires_at
            assignment.save(update_fields=["is_active", "expires_at", "updated_at"])
            accounts[role_code] = {
                "username": username,
                "password": password,
                "branch_code": branch.code if branch else None,
                "is_active": True,
            }

        inactive_password = f"Smk!{secrets.token_urlsafe(22)}aA9"
        inactive_username = f"smoke.role.{run_id}.inactive"[:150]
        inactive, _ = User.objects.update_or_create(
            username=inactive_username,
            defaults={
                "email": f"{inactive_username}@vinova.invalid",
                "first_name": "SMOKE",
                "last_name": "inactive",
                "is_active": False,
                "is_staff": False,
                "is_superuser": False,
            },
        )
        inactive.set_password(inactive_password)
        inactive.save(update_fields=["password"])
        accounts["inactive"] = {
            "username": inactive_username,
            "password": inactive_password,
            "branch_code": None,
            "is_active": False,
        }
        return {
            "schema_version": 1,
            "run_id": run_id,
            "environment": os.getenv("VINOVA_ENVIRONMENT", "local"),
            "created_at": timezone.now().isoformat(),
            "expires_at": expires_at.isoformat(),
            "accounts": accounts,
            "branches": [branch.code for branch in branches],
            "vehicle_catalog": {"brand": brand.name, "model": vehicle_model.name},
        }

    @staticmethod
    def _technical_ruc(run_id: str) -> str:
        """Genera un identificador numérico de 13 dígitos para staging.

        No pretende representar un contribuyente real. Su objetivo es respetar
        la longitud esperada por la configuración SRI y evitar que los datos
        técnicos del smoke provoquen errores de base de datos.
        """
        digest = hashlib.sha256(run_id.encode("utf-8")).hexdigest()
        body = int(digest[:10], 16) % 10_000_000
        return f"999{body:07d}001"

    @transaction.atomic
    def _disable(self, run_id: str) -> int:
        users = User.objects.filter(username__startswith=f"smoke.role.{run_id}.")
        count = users.update(is_active=False)
        UserRole.objects.filter(user__username__startswith=f"smoke.role.{run_id}.").update(is_active=False)
        Branch.objects.filter(code__startswith=f"smoke-{run_id}-").update(is_active=False, is_public=False)
        Company.objects.filter(
            Q(email=f"smoke.roles.{run_id}@vinova.invalid") | Q(ruc=f"SMOKE{run_id[:15]}")
        ).update(is_active=False)
        VehicleModel.objects.filter(brand__name=f"SMOKE-{run_id}").update(is_active=False)
        VehicleBrand.objects.filter(name=f"SMOKE-{run_id}").update(is_active=False)
        return count
