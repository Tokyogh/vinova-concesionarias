"""ES: Este módulo especifica regresiones ejecutables para el dominio de cuentas.

EN: This module specifies executable regressions for the accounts domain.

Contexto existente / Existing context:
Regression coverage for roles in the accounts domain.
"""

import pytest

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.branches.models import Branch
from apps.companies.models import Company


@pytest.mark.django_db
def test_user_can_have_multiple_roles(django_user_model):
    company = Company.objects.create(
        legal_name="Empresa Demo S.A.",
        commercial_name="Empresa Demo",
        ruc="1790000000002",
    )
    branch = Branch.objects.create(
        company=company,
        name="Sucursal Demo",
        code="SUC-DEMO-2",
        branch_type=Branch.BranchType.DEALERSHIP,
        city="Guayaquil",
    )
    user = django_user_model.objects.create_user(username="ana", email="ana@example.com", password="x")
    p1 = PermissionCode.objects.create(module="vehicles", code="vehicles.view", name="Ver vehículos")
    p2 = PermissionCode.objects.create(module="sales", code="sales.quote", name="Cotizar")
    r1 = Role.objects.create(code="vendedor", name="Vendedor")
    r1.permissions.add(p1)
    r2 = Role.objects.create(code="facturacion", name="Facturación")
    r2.permissions.add(p2)
    UserRole.objects.create(user=user, role=r1, branch=branch)
    UserRole.objects.create(user=user, role=r2, branch=branch)
    assert user.has_perm_code("vehicles.view")
    assert user.has_perm_code("sales.quote")
