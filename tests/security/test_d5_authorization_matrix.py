"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for d5 authorization matrix in the security domain.
"""

from __future__ import annotations

from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.accounts.scopes import accessible_branch_ids
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.documents.models import PrivateDocument
from apps.documents.selectors import (
    has_global_document_scope,
    private_documents_queryset,
)
from apps.imports.models import ImportBatch


def _permission(module: str, code: str) -> PermissionCode:
    return PermissionCode.objects.create(module=module, code=code, name=code)


def _branch_user(django_user_model, *, username, branch, permissions):
    # ES: force_login no necesita una contraseña utilizable en estas pruebas.
    # EN: force_login does not need a usable password in these tests.
    user = django_user_model.objects.create_user(
        username=username, email=f"{username}@example.com", password=None
    )
    role = Role.objects.create(code=f"role_{username}", name=username)
    role.permissions.set(permissions)
    UserRole.objects.create(user=user, role=role, branch=branch)
    return user


def _company_and_branches():
    company = Company.objects.create(
        legal_name="Vinova Auditoria S.A.",
        commercial_name="Vinova",
        ruc="1799999999001",
    )
    branch_a = Branch.objects.create(company=company, name="Norte", code="NOR", city="Quito")
    branch_b = Branch.objects.create(company=company, name="Sur", code="SUR", city="Guayaquil")
    return company, branch_a, branch_b


def _import_batch(*, branch, uploader, filename="clientes-1.csv"):
    return ImportBatch.objects.create(
        import_type=ImportBatch.ImportType.CUSTOMERS,
        status=ImportBatch.Status.UPLOADED,
        original_file=SimpleUploadedFile(filename, b"nombre,cedula\nAna,1712345678\n"),
        original_filename=filename,
        file_hash=filename,
        file_size=64,
        uploaded_by=uploader,
        default_branch=branch,
        total_rows=1,
        valid_rows=1,
        notes="lote de prueba d5",
    )


@pytest.fixture(name="imports_ctx")
def imports_ctx_fixture(django_user_model):
    company, branch_a, branch_b = _company_and_branches()
    perm = _permission("imports", "imports.manage")
    owner = django_user_model.objects.create_user(
        username="d5_owner", email="d5_owner@example.com", password="x"
    )
    scoped = _branch_user(
        django_user_model, username="d5_scoped", branch=branch_a, permissions=[perm]
    )
    batch_a = _import_batch(branch=branch_a, uploader=owner, filename="batch-a.csv")
    batch_b = _import_batch(branch=branch_b, uploader=owner, filename="batch-b.csv")
    return {
        "company": company,
        "branch_a": branch_a,
        "branch_b": branch_b,
        "user": scoped,
        "batch_a": batch_a,
        "batch_b": batch_b,
    }


@pytest.mark.django_db
def test_imports_detail_is_branch_scoped(imports_ctx, client):
    ctx = imports_ctx
    client.force_login(ctx["user"])

    own = client.get(f"/dashboard/imports/{ctx['batch_a'].pk}/")
    foreign = client.get(f"/dashboard/imports/{ctx['batch_b'].pk}/")

    assert own.status_code == 200
    assert foreign.status_code == 404


@pytest.mark.django_db
def test_imports_revalidate_denies_other_branch(imports_ctx, client):
    ctx = imports_ctx
    client.force_login(ctx["user"])

    response = client.post(f"/dashboard/imports/{ctx['batch_b'].pk}/revalidate/")

    assert response.status_code == 404


@pytest.mark.django_db
def test_imports_confirm_denies_other_branch(imports_ctx, client):
    ctx = imports_ctx
    client.force_login(ctx["user"])
    batch = ctx["batch_b"]
    status_before = batch.status

    response = client.post(f"/dashboard/imports/{batch.pk}/confirm/")

    batch.refresh_from_db()
    assert response.status_code == 404
    assert batch.status == status_before


@pytest.mark.django_db
def test_imports_home_does_not_list_other_branch_batches(imports_ctx, client):
    ctx = imports_ctx
    client.force_login(ctx["user"])

    response = client.get("/dashboard/imports/")

    assert response.status_code == 200
    content = response.content.decode(response.charset, errors="replace")
    assert ctx["batch_a"].original_filename in content
    assert ctx["batch_b"].original_filename not in content


@pytest.mark.django_db
def test_imports_scope_defaults_to_no_access_without_permission(django_user_model, client):
    _company_and_branches()
    user = django_user_model.objects.create_user(
        username="d5_noperm", email="d5_noperm@example.com", password="x"
    )
    client.force_login(user)

    response = client.get("/dashboard/imports/")

    assert response.status_code == 403


@pytest.mark.django_db
def test_accessible_branch_ids_uses_role_validity_window(django_user_model):
    company, branch_a, _ = _company_and_branches()
    perm = _permission("imports", "imports.manage")
    role = Role.objects.create(code="d5_window_role", name="d5 window role")
    role.permissions.add(perm)
    user = django_user_model.objects.create_user(
        username="d5_window", email="d5_window@example.com", password="x"
    )
    assignment = UserRole.objects.create(user=user, role=role, branch=branch_a)
    assert accessible_branch_ids(user, permission_codes=("imports.manage",)) == (branch_a.pk,)

    assignment.expires_at = timezone.now() - timedelta(seconds=1)
    assignment.save(update_fields=["expires_at", "updated_at"])

    assert accessible_branch_ids(user, permission_codes=("imports.manage",)) == ()


@pytest.mark.django_db
def test_expired_global_role_stops_granting_global_document_scope(django_user_model):
    company, branch_a, _ = _company_and_branches()
    perm = _permission("documents", "documents.view")
    role = Role.objects.create(code="d5_docs_global", name="d5 docs global")
    role.permissions.add(perm)
    user = django_user_model.objects.create_user(
        username="d5_docs_global", email="d5_docs_global@example.com", password="x"
    )
    UserRole.objects.create(user=user, role=role, branch=None)
    assert has_global_document_scope(user) is True

    assignment = user.user_roles.get()
    assignment.expires_at = timezone.now() - timedelta(seconds=1)
    assignment.save(update_fields=["expires_at", "updated_at"])

    assert has_global_document_scope(user) is False


@pytest.mark.django_db
def test_expired_branch_role_stops_granting_document_branch_scope(django_user_model):
    company, branch_a, branch_b = _company_and_branches()
    perm = _permission("documents", "documents.view")
    role = Role.objects.create(code="d5_docs_branch", name="d5 docs branch")
    role.permissions.add(perm)
    owner = django_user_model.objects.create_user(
        username="d5_docs_owner", email="d5_docs_owner@example.com", password="x"
    )
    user = _branch_user(
        django_user_model, username="d5_docs_branch", branch=branch_a, permissions=[perm]
    )
    assignment = user.user_roles.get()
    assignment.expires_at = timezone.now() - timedelta(seconds=1)
    assignment.save(update_fields=["expires_at", "updated_at"])

    own_doc = PrivateDocument.objects.create(
        title="Contrato A",
        original_name="contrato-a.pdf",
        document_type="contract",
        branch=branch_a,
        uploaded_by=owner,
        file_hash="a" * 64,
        size_bytes=10,
        extension="pdf",
        mime_type="application/pdf",
    )
    other_doc = PrivateDocument.objects.create(
        title="Contrato B",
        original_name="contrato-b.pdf",
        document_type="contract",
        branch=branch_b,
        uploaded_by=owner,
        file_hash="b" * 64,
        size_bytes=10,
        extension="pdf",
        mime_type="application/pdf",
    )

    assert list(private_documents_queryset(user=user)) == []
    assert own_doc not in private_documents_queryset(user=user)
    assert other_doc not in private_documents_queryset(user=user)


@pytest.mark.django_db
def test_document_scope_deny_by_default_for_unauthenticated():
    assert has_global_document_scope(None) is False
    assert list(private_documents_queryset(user=None)) == []
