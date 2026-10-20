# -*- coding: utf-8 -*-
"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
D7 — provisioning y matriz real de cuentas QA por rol.

Ejecuta el comando de aprovisionamiento contra la base de prueba (nunca
imprime credenciales: el documento con claves solo existe en memoria y en
private/qa_credentials.txt, que está fuera de Git). verifica que los 13 roles
reales quedan provisionados, con asignación de rol/sucursal correcta y que el
login + acceso autorizado 200 + acceso denegado 403 se cumplen para cada rol.
"""
from __future__ import annotations

import pytest
from django.core.management import call_command

from apps.accounts.management.commands.provision_qa_role_accounts import (
    AUTHORIZATION_PROBES,
    BRANCH_REQUIRED_ROLE_CODES,
    Command,
)
from apps.accounts.models import Role

EXPECTED_ROLE_CODES = {
    "superadmin",
    "admin_general",
    "admin_sucursal",
    "gerente_comercial",
    "jefe_inventario",
    "vendedor",
    "asesor_postventa",
    "facturacion",
    "bodega",
    "marketing",
    "soporte_cliente",
    "auditor",
    "cliente",
}


@pytest.mark.django_db
def test_provisioning_covers_every_real_role_and_validates_matrix():
    call_command("seed_roles", verbosity=0)
    roles = list(Role.objects.filter(is_active=True).order_by("level", "name"))

    assert {role.code for role in roles} == EXPECTED_ROLE_CODES
    assert len(AUTHORIZATION_PROBES) == len(EXPECTED_ROLE_CODES)

    command = Command()
    document = command._provision(roles)

    for role in roles:
        assert f"ROL: {role.name}" in document
        assert f"USUARIO/EMAIL: qa.{role.code}@example.invalid" in document


@pytest.mark.django_db
def test_roles_with_branch_scope_are_assigned_to_qa_branch(django_user_model):
    call_command("seed_roles", verbosity=0)
    roles = list(Role.objects.filter(is_active=True).order_by("level", "name"))
    command = Command()
    branch = command._qa_branch()

    command._provision(roles)

    for role in roles:
        user = django_user_model.objects.get(username=f"qa.{role.code}")
        assignments = user.active_role_assignments()
        assert assignments.count() == 1
        assignment = assignments.get()
        assert assignment.role_id == role.pk
        if role.code in BRANCH_REQUIRED_ROLE_CODES:
            assert assignment.branch_id == branch.pk
        else:
            assert assignment.branch_id is None
        # Ninguna cuenta QA debe heredar flags de privilegio Django.
        assert not user.is_superuser and not user.is_staff
        assert not user.groups.exists() and not user.user_permissions.exists()