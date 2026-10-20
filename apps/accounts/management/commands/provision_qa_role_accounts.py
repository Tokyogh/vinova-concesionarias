"""ES: Implementa el comando administrativo «provision qa role accounts» para cuentas.

EN: Implements the «provision qa role accounts» management command for accounts.

Contexto existente / Existing context:
Django management command for provision qa role accounts.
"""

from __future__ import annotations

import hashlib
import os
import secrets
import tempfile
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.test import Client

from apps.accounts.forms import BRANCH_REQUIRED_ROLE_CODES
from apps.accounts.models import Role, UserRole
from apps.accounts.qa_safety import assert_non_production_database
from apps.accounts.scopes import accessible_branch_ids
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer

User = get_user_model()

# A real page for each role's dashboard family, plus a route outside that role.
AUTHORIZATION_PROBES = {
    "superadmin": ("/dashboard/admin/", None),
    "admin_general": ("/dashboard/admin/", None),
    "admin_sucursal": ("/dashboard/branch/", "/dashboard/admin/"),
    "gerente_comercial": ("/dashboard/commercial/", "/dashboard/inventory-home/"),
    "jefe_inventario": ("/dashboard/inventory-home/", "/dashboard/seller/"),
    "vendedor": ("/dashboard/seller/", "/dashboard/admin/"),
    "asesor_postventa": ("/dashboard/support/", "/dashboard/seller/"),
    "facturacion": ("/dashboard/billing/", "/dashboard/inventory-home/"),
    "bodega": ("/dashboard/inventory-home/", "/dashboard/seller/"),
    "marketing": ("/dashboard/marketing/", "/dashboard/seller/"),
    "soporte_cliente": ("/dashboard/support/", "/dashboard/seller/"),
    "auditor": ("/dashboard/auditor/", "/dashboard/admin/"),
    "cliente": ("/mi-cuenta/", "/dashboard/admin/"),
}

BRANCH_SCOPE_PROBES = {
    "admin_sucursal": "vehicles.view",
    "jefe_inventario": "inventory.view",
    "vendedor": "customers.view",
    "asesor_postventa": "post_sales.view",
    "facturacion": "invoices.view",
    "bodega": "inventory.view",
}

GLOBAL_SCOPE_PROBES = {
    "superadmin": "accounts.manage_users",
    "admin_general": "accounts.manage_users",
    "gerente_comercial": "sales.quote",
    "marketing": "vehicles.manage",
    "soporte_cliente": "privacy.view",
    "auditor": "audit.view",
}


class Command(BaseCommand):
    """Provision repeatable non-production accounts for the active role matrix."""

    help = "Crea una cuenta QA con alcance real por cada rol activo y guarda las claves en private/qa_credentials.txt."

    def handle(self, *args, **options):
        self._assert_development_target()
        roles = list(Role.objects.filter(is_active=True).prefetch_related("permissions").order_by("level", "name"))
        if not roles:
            raise CommandError("No hay roles activos en la base de datos.")
        unknown = sorted({role.code for role in roles} - AUTHORIZATION_PROBES.keys())
        if unknown:
            raise CommandError("Faltan pruebas de autorización para roles activos: " + ", ".join(unknown))

        document = self._provision(roles)
        destination = Path(settings.BASE_DIR) / "private" / "qa_credentials.txt"
        self._write_private_file(destination, document)
        names = ", ".join(role.name for role in roles)
        self.stdout.write(self.style.SUCCESS(f"Cuentas QA validadas: {len(roles)}. Roles: {names}."))
        self.stdout.write("Credenciales escritas únicamente en private/qa_credentials.txt.")

    @staticmethod
    def _assert_development_target() -> None:
        assert_non_production_database()

    @transaction.atomic
    def _provision(self, roles: list[Role]) -> str:
        branch_roles = [role for role in roles if role.code in BRANCH_REQUIRED_ROLE_CODES]
        branch = self._qa_branch() if branch_roles else None
        credentials = []

        for role in roles:
            username = f"qa.{role.code}"
            email = f"{username}@example.invalid"
            user = self._get_or_create_qa_user(username=username, email=email, role=role, branch=branch if role in branch_roles else None)
            password = f"Q9!{secrets.token_urlsafe(32)}aA"
            user.set_password(password)
            user.save(update_fields=["password"])
            user.groups.clear()
            user.user_permissions.clear()

            assignment_branch = branch if role.code in BRANCH_REQUIRED_ROLE_CODES else None
            UserRole.objects.filter(user=user).exclude(role=role, branch=assignment_branch).update(is_active=False)
            assignment, _ = UserRole.objects.get_or_create(user=user, role=role, branch=assignment_branch)
            assignment.is_active = True
            assignment.starts_at = None
            assignment.expires_at = None
            assignment.assigned_by = None
            assignment.save(update_fields=["is_active", "starts_at", "expires_at", "assigned_by", "updated_at"])

            if role.code == "cliente":
                self._ensure_client_profile(user=user, branch=branch)

            allowed_path, denied_path = AUTHORIZATION_PROBES[role.code]
            self._validate_account(
                role=role,
                user=user,
                password=password,
                branch=assignment_branch,
                allowed_path=allowed_path,
                denied_path=denied_path,
            )
            scope = f"Sucursal QA: {branch.name} ({branch.code})" if assignment_branch else "Global (sin sucursal)"
            credentials.append(
                "\n".join(
                    (
                        f"ROL: {role.name}",
                        f"USUARIO/EMAIL: {email}",
                        f"CONTRASE\u00d1A: {password}",
                        f"SUCURSAL/ALCANCE: {scope}",
                        "--------------------------------",
                    )
                )
            )

        return "\n".join(("VINOVA PRO \u2014 CUENTAS DE PRUEBA", "================================", *credentials, ""))

    @staticmethod
    def _qa_branch() -> Branch:
        digest = hashlib.sha256(b"vinova-pro-qa-role-accounts").hexdigest()
        numeric = int(digest[:10], 16) % 10_000_000
        ruc = f"999{numeric:07d}001"
        company, _ = Company.objects.get_or_create(
            ruc=ruc,
            defaults={
                "legal_name": "QA Organization — VINOVA PRO",
                "commercial_name": "QA Roles VINOVA PRO",
                "email": "qa.role.accounts@example.invalid",
                "is_active": True,
            },
        )
        if not company.commercial_name.startswith("QA Roles"):
            raise CommandError("El identificador reservado de compañía QA ya pertenece a datos no sintéticos.")
        branch, _ = Branch.objects.get_or_create(
            company=company,
            code="qa-role-scope",
            defaults={
                "name": "QA Sucursal de pruebas",
                "branch_type": Branch.BranchType.DEALERSHIP,
                "city": "QA Lab",
                "address": "Datos sintéticos de pruebas",
                "email": "qa.branch@example.invalid",
                "is_public": False,
                "is_active": True,
            },
        )
        if not branch.name.startswith("QA "):
            raise CommandError("El código reservado de sucursal QA ya pertenece a datos no sintéticos.")
        if not branch.is_active:
            branch.is_active = True
            branch.is_public = False
            branch.save(update_fields=["is_active", "is_public", "updated_at"])
        return branch

    @staticmethod
    def _get_or_create_qa_user(*, username: str, email: str, role: Role, branch: Branch | None) -> User:
        by_username = User.objects.filter(username__iexact=username).first()
        by_email = User.objects.filter(email__iexact=email).first()
        if by_username and by_email and by_username.pk != by_email.pk:
            raise CommandError(f"Colisión de identidad QA para el rol {role.code}; no se modificó ninguna cuenta.")
        user = by_username or by_email
        if user:
            if user.username != username or user.email != email or user.first_name != "QA":
                raise CommandError(f"La identidad reservada qa.{role.code} ya existe y no parece sintética; no se modificó.")
            user.last_name = role.name
            user.branch = branch
            user.is_active = True
            user.is_staff = False
            user.is_superuser = False
            user.must_change_password = False
            user.failed_login_count = 0
            user.locked_until = None
            user.save(
                update_fields=[
                    "last_name", "branch", "is_active", "is_staff", "is_superuser",
                    "must_change_password", "failed_login_count", "locked_until",
                ]
            )
            return user

        return User.objects.create_user(
            username=username,
            email=email,
            password=None,
            first_name="QA",
            last_name=role.name,
            branch=branch,
            is_active=True,
            is_staff=False,
            is_superuser=False,
            must_change_password=False,
        )

    @staticmethod
    def _ensure_client_profile(*, user: User, branch: Branch | None) -> Customer:
        customer = Customer.objects.filter(account=user).first()
        if customer is None:
            customer = Customer.objects.create(
                first_name="QA",
                last_name="Cliente",
                email=user.email,
                status=Customer.Status.ACTIVE,
                assigned_branch=branch,
                account=user,
            )
        elif customer.email != user.email or customer.first_name != "QA":
            raise CommandError("La cuenta QA cliente ya está vinculada a un expediente no sintético.")
        else:
            customer.last_name = "Cliente"
            customer.status = Customer.Status.ACTIVE
            customer.assigned_branch = branch
            customer.is_deleted = False
            customer.deleted_at = None
            customer.save(
                update_fields=[
                    "last_name",
                    "status",
                    "assigned_branch",
                    "is_deleted",
                    "deleted_at",
                    "updated_at",
                ]
            )
        return customer

    @staticmethod
    def _validate_account(
        *,
        role: Role,
        user: User,
        password: str,
        branch: Branch | None,
        allowed_path: str,
        denied_path: str | None,
    ) -> None:
        if user.is_superuser or user.is_staff:
            raise CommandError(f"La cuenta QA del rol {role.code} recibió un flag de privilegio Django inesperado.")
        active_assignments = list(user.active_role_assignments().select_related("role", "branch"))
        expected_branch = branch if role.code in BRANCH_REQUIRED_ROLE_CODES else None
        if len(active_assignments) != 1 or active_assignments[0].role_id != role.pk or active_assignments[0].branch_id != getattr(expected_branch, "pk", None):
            raise CommandError(f"La asignación de rol/sucursal QA no coincide para {role.code}.")
        if user.groups.exists() or user.user_permissions.exists():
            raise CommandError(f"La cuenta QA del rol {role.code} tiene permisos directos inesperados.")

        branch_probe = BRANCH_SCOPE_PROBES.get(role.code)
        global_probe = GLOBAL_SCOPE_PROBES.get(role.code)
        if branch_probe:
            if not role.permissions.filter(code=branch_probe).exists():
                raise CommandError(f"Falta el permiso de alcance esperado para {role.code}.")
            scope = accessible_branch_ids(user, permission_codes=(branch_probe,))
            if scope != (expected_branch.pk,):
                raise CommandError(f"El alcance QA de sucursal no quedó aislado para {role.code}.")
        elif global_probe:
            if not role.permissions.filter(code=global_probe).exists():
                raise CommandError(f"Falta el permiso global esperado para {role.code}.")
            if accessible_branch_ids(user, permission_codes=(global_probe,)) is not None:
                raise CommandError(f"El alcance QA global no coincide para {role.code}.")
        elif role.code == "cliente":
            if user.can_access_internal_panel or accessible_branch_ids(user, permission_codes=("vehicles.view",)) != ():
                raise CommandError("La cuenta QA de cliente recibió acceso interno o de sucursal.")

        client = Client()
        if not client.login(username=user.email, password=password):
            raise CommandError(f"Falló la autenticación de la cuenta QA del rol {role.code}.")
        allowed = client.get(allowed_path)
        if allowed.status_code != 200:
            raise CommandError(f"El rol {role.code} no pudo abrir su vista autorizada ({allowed.status_code}).")
        if denied_path:
            denied = client.get(denied_path)
            if denied.status_code != 403:
                raise CommandError(f"El rol {role.code} obtuvo acceso inesperado a una vista ajena ({denied.status_code}).")

    @staticmethod
    def _write_private_file(destination: Path, content: str) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                newline="\n",
                prefix=".qa_credentials_",
                suffix=".tmp",
                dir=destination.parent,
                delete=False,
            ) as handle:
                temp_path = Path(handle.name)
                handle.write(content)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.chmod(temp_path, 0o600)
            except OSError:
                pass
            os.replace(temp_path, destination)
            try:
                os.chmod(destination, 0o600)
            except OSError:
                pass
        finally:
            if temp_path and temp_path.exists():
                temp_path.unlink()
