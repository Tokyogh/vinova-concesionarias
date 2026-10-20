"""ES: Este módulo especifica regresiones ejecutables para el dominio de seguridad.

EN: This module specifies executable regressions for the security center domain.

Contexto existente / Existing context:
Regression coverage for document scope in the security_center domain.
"""

from __future__ import annotations

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.documents.models import PrivateDocument
from apps.documents.selectors import private_documents_queryset

pytestmark = pytest.mark.django_db


def test_branch_scoped_user_only_sees_own_private_documents(django_user_model, settings, tmp_path):
    settings.PRIVATE_STORAGE_ROOT = tmp_path / "private"
    company = Company.objects.create(legal_name="Empresa", commercial_name="Empresa", ruc="1799999999001")
    branch_a = Branch.objects.create(company=company, name="Norte", code="norte", city="Quito")
    branch_b = Branch.objects.create(company=company, name="Sur", code="sur", city="Quito")
    user = django_user_model.objects.create_user(username="branchuser", email="branch@example.com", password="Strong!Pass123")
    permission = PermissionCode.objects.create(module="documents", code="documents.view", name="Ver documentos")
    role = Role.objects.create(code="branch-docs", name="Documentos de sucursal", level=30)
    role.permissions.add(permission)
    UserRole.objects.create(user=user, role=role, branch=branch_a)
    doc_a = PrivateDocument.objects.create(title="Documento A", document_type="other", branch=branch_a, file=SimpleUploadedFile("a.pdf", b"A", content_type="application/pdf"))
    PrivateDocument.objects.create(title="Documento B", document_type="other", branch=branch_b, file=SimpleUploadedFile("b.pdf", b"B", content_type="application/pdf"))
    assert list(private_documents_queryset(user=user)) == [doc_a]


def test_branch_scoped_user_cannot_archive_asset_from_other_branch(client, django_user_model, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    company = Company.objects.create(legal_name="Empresa 2", commercial_name="Empresa 2", ruc="1799999999002")
    branch_a = Branch.objects.create(company=company, name="Este", code="este", city="Quito")
    branch_b = Branch.objects.create(company=company, name="Oeste", code="oeste", city="Quito")
    user = django_user_model.objects.create_user(username="assetbranch", email="assetbranch@example.com", password="Strong!Pass123")
    permission = PermissionCode.objects.create(module="documents", code="documents.manage", name="Gestionar documentos")
    role = Role.objects.create(code="branch-assets", name="Recursos de sucursal", level=30)
    role.permissions.add(permission)
    UserRole.objects.create(user=user, role=role, branch=branch_a)
    from apps.documents.models import ReusableAsset
    asset = ReusableAsset.objects.create(
        title="Recurso ajeno",
        asset_type=ReusableAsset.AssetType.GENERAL,
        visibility=ReusableAsset.Visibility.INTERNAL,
        branch=branch_b,
        file=SimpleUploadedFile("other.pdf", b"OTHER", content_type="application/pdf"),
    )
    client.force_login(user)
    response = client.post(f"/dashboard/documents/assets/{asset.pk}/archive/")
    assert response.status_code == 404
    asset.refresh_from_db()
    assert asset.is_deleted is False
