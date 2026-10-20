"""ES: Este módulo especifica regresiones ejecutables para el dominio de documentos.

EN: This module specifies executable regressions for the documents domain.

Contexto existente / Existing context:
Regression coverage for uploads security in the documents domain.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.documents.models import DocumentCategory, PrivateDocument, ReusableAsset
from apps.documents.selectors import allowed_document_branch_ids, private_documents_queryset
from apps.documents.services import (
    archive_private_document,
    create_private_document,
    create_reusable_asset,
    register_document_download,
    update_private_document,
    update_reusable_asset,
)

TRAVERSAL_ATTEMPT = "../../../../etc/secret.pdf"


def _context(django_user_model):
    company = Company.objects.create(legal_name="Docs S.A.", commercial_name="Docs", ruc="1799999999002")
    branches = [Branch.objects.create(company=company, name=f"Sede {i}", code=f"DOC-{i}", city="Quito") for i in (1, 2)]
    perm_view = PermissionCode.objects.create(module="documents", code="documents.view", name="Ver docs")
    perm_manage = PermissionCode.objects.create(module="documents", code="documents.manage", name="Gestionar docs")
    perm_download = PermissionCode.objects.create(
        module="documents", code="documents.download_private", name="Descargar docs"
    )
    return company, branches, perm_view, perm_manage, perm_download


def _branch_user(django_user_model, *, branch, perms, code="docs_branch"):
    user = django_user_model.objects.create_user(username=code, email=f"{code}@example.com", password="x")
    role = Role.objects.create(code=code, name=code)
    role.permissions.add(*perms)
    UserRole.objects.create(user=user, role=role, branch=branch)
    return user


def _superuser(django_user_model):
    return django_user_model.objects.create_superuser(username="docs_admin", email="admin@example.com", password="x")


def _category():
    return DocumentCategory.objects.create(name="Contratos", scope=DocumentCategory.Scope.SALE)


def _private_document(*, branch, user, filename="contrato.pdf", category=None, type_code="contract"):
    from apps.documents.forms import PrivateDocumentForm

    file = SimpleUploadedFile(filename, b"%PDF-1.4 fake", content_type="application/pdf")
    form = PrivateDocumentForm(
        data={
            "title": "Contrato",
            "document_type": type_code,
            "category": category.pk if category else "",
            "branch": branch.pk,
            "status": PrivateDocument.Status.ACTIVE,
            "is_confidential": True,
        },
        files={"file": file},
        user=user,
    )
    assert form.is_valid(), form.errors
    return create_private_document(actor=user, form=form)


def _private_document_update_form(*, document, user, filename):
    from apps.documents.forms import PrivateDocumentForm

    form = PrivateDocumentForm(
        data={
            "title": document.title,
            "document_type": document.document_type,
            "category": document.category_id or "",
            "branch": document.branch_id or "",
            "status": document.status,
            "customer": document.customer_id or "",
            "vehicle": document.vehicle_id or "",
            "sale": document.sale_id or "",
            "expires_at": document.expires_at or "",
            "is_confidential": document.is_confidential,
            "notes": document.notes,
        },
        files={"file": SimpleUploadedFile(filename, b"%PDF-1.4 replacement", content_type="application/pdf")},
        instance=document,
        user=user,
    )
    assert form.is_valid(), form.errors
    return form


@pytest.mark.django_db
def test_extension_allowlist_blocks_dangerous_upload(django_user_model):
    company, branches, *_ = _context(django_user_model)
    category = _category()
    for bad in ("malware.exe", "shell.php", "x.html", "evil.js", "payload.svg"):
        doc = PrivateDocument(
            title="P", document_type=PrivateDocument.DocumentType.CONTRACT, branch=branches[0], category=category
        )
        with pytest.raises(ValidationError):
            doc.file = SimpleUploadedFile(bad, b"x")
            doc.full_clean()


@pytest.mark.django_db
def test_upload_size_limit_enforced(django_user_model, settings):
    company, branches, *_ = _context(django_user_model)
    doc = PrivateDocument(
        title="P", document_type=PrivateDocument.DocumentType.CONTRACT, branch=branches[0], category=_category()
    )
    oversized = SimpleUploadedFile("grande.pdf", b"x" * (settings.VINOVA_MAX_UPLOAD_MB * 1024 * 1024 + 1))
    with pytest.raises(ValidationError):
        doc.file = oversized
        doc.full_clean()


@pytest.mark.django_db
def test_stored_path_never_uses_client_filename(django_user_model, tmp_path):
    company, branches, perm_manage, *_ = _context(django_user_model)
    manager = _branch_user(django_user_model, branch=branches[0], perms=[perm_manage])
    doc = _private_document(branch=branches[0], user=manager, filename=TRAVERSAL_ATTEMPT)
    rel = str(doc.file.name)
    assert ".." not in rel
    assert "/etc" not in rel
    assert "secret" not in rel
    assert Path(rel).parent.name == "contract"


@pytest.mark.django_db
def test_private_storage_root_is_not_public_media(django_user_model, settings, client):
    company, branches, perm_manage, *_ = _context(django_user_model)
    admin = _superuser(django_user_model)
    manager = _branch_user(django_user_model, branch=branches[0], perms=[perm_manage])
    doc = _private_document(branch=branches[0], user=manager)
    assert ".." not in str(doc.file.name)
    assert str(doc.file.name).startswith("documents/")
    physical = settings.PRIVATE_STORAGE_ROOT / doc.file.name
    assert settings.MEDIA_ROOT not in physical.parents, "El archivo privado no debe residir en el árbol MEDIA_ROOT"
    client.force_login(admin)
    assert client.get(doc.file.url).status_code == 404


@pytest.mark.django_db
def test_metadata_sanitizes_original_name_and_mime(django_user_model):
    company, branches, perm_manage, *_ = _context(django_user_model)
    manager = _branch_user(django_user_model, branch=branches[0], perms=[perm_manage])
    doc = _private_document(branch=branches[0], user=manager, filename="../../evas/../../reporte_final.pdf")
    assert ".." not in doc.original_name
    assert doc.original_name == "reporte_final.pdf"
    assert doc.extension == ".pdf"
    assert doc.size_bytes > 0
    assert len(doc.file_hash) == 64


@pytest.mark.django_db
def test_download_requires_permission(django_user_model, client):
    company, branches, perm_manage, perm_view, perm_download = _context(django_user_model)
    manager = _branch_user(django_user_model, branch=branches[0], perms=[perm_manage], code="doc_mgr")
    viewer = _branch_user(django_user_model, branch=branches[0], perms=[perm_view], code="doc_viewer")
    doc = _private_document(branch=branches[0], user=manager)
    client.force_login(viewer)
    assert client.get(f"/dashboard/documents/{doc.pk}/download/").status_code in (403, 404)


@pytest.mark.django_db
def test_branch_scoped_user_cannot_download_other_branch(django_user_model, client):
    company, branches, perm_manage, perm_view, perm_download = _context(django_user_model)
    manager_a = _branch_user(django_user_model, branch=branches[0], perms=[perm_manage, perm_download], code="mgr_a")
    user_b = _branch_user(django_user_model, branch=branches[1], perms=[perm_download, perm_view], code="user_b")
    doc_a = _private_document(branch=branches[0], user=manager_a)
    client.force_login(user_b)
    resp = client.get(f"/dashboard/documents/{doc_a.pk}/download/")
    assert resp.status_code == 404


@pytest.mark.django_db
def test_superuser_download_succeeds(django_user_model, client):
    company, branches, perm_manage, *_ = _context(django_user_model)
    admin = _superuser(django_user_model)
    manager = _branch_user(django_user_model, branch=branches[0], perms=[perm_manage])
    doc = _private_document(branch=branches[0], user=manager)
    client.force_login(admin)
    resp = client.get(f"/dashboard/documents/{doc.pk}/download/")
    assert resp.status_code == 200
    assert "nosniff" in resp["X-Content-Type-Options"]
    assert resp["Content-Disposition"].startswith("attachment")


@pytest.mark.django_db
def test_reusable_asset_upload_validation(django_user_model):
    from apps.documents.forms import ReusableAssetForm

    company, branches, perm_manage, *_ = _context(django_user_model)
    manager = _branch_user(django_user_model, branch=branches[0], perms=[perm_manage])
    form = ReusableAssetForm(
        data={
            "title": "Logo",
            "asset_type": ReusableAsset.AssetType.BRAND_LOGO,
            "visibility": ReusableAsset.Visibility.INTERNAL,
            "branch": branches[0].pk,
            "is_active": True,
        },
        files={"file": SimpleUploadedFile("logo.png", b"\x89PNG\r\n\x1a\n", content_type="image/png")},
        user=manager,
    )
    assert form.is_valid(), form.errors
    asset = create_reusable_asset(actor=manager, form=form)
    assert ".." not in str(asset.file.name)
    assert asset.file_hash == "4c4b6a3be1314ab86138bef4314dde022e600960d8689a2c8f8631802d20dab6"


@pytest.mark.django_db
def test_reusable_asset_replacement_removes_old_file_after_commit(
    django_user_model,
    django_capture_on_commit_callbacks,
):
    from apps.documents.forms import ReusableAssetForm

    _, branches, perm_manage, *_ = _context(django_user_model)
    manager = _branch_user(django_user_model, branch=branches[0], perms=[perm_manage])
    create_form = ReusableAssetForm(
        data={
            "title": "Logo",
            "asset_type": ReusableAsset.AssetType.BRAND_LOGO,
            "visibility": ReusableAsset.Visibility.INTERNAL,
            "branch": branches[0].pk,
            "is_active": True,
        },
        files={"file": SimpleUploadedFile("logo.png", b"\x89PNG\r\n\x1a\n", content_type="image/png")},
        user=manager,
    )
    assert create_form.is_valid(), create_form.errors
    asset = create_reusable_asset(actor=manager, form=create_form)
    old_name = asset.file.name
    storage = asset.file.storage
    update_form = ReusableAssetForm(
        data={
            "title": "Logo actualizado",
            "asset_type": asset.asset_type,
            "visibility": asset.visibility,
            "branch": asset.branch_id,
            "is_active": True,
        },
        files={"file": SimpleUploadedFile("logo-new.png", b"\x89PNG\r\n\x1a\nnew", content_type="image/png")},
        instance=asset,
        user=manager,
    )
    assert update_form.is_valid(), update_form.errors

    with django_capture_on_commit_callbacks(execute=True):
        updated = update_reusable_asset(actor=manager, asset=asset, form=update_form)

    assert updated.file.name != old_name
    assert storage.exists(updated.file.name)
    assert not storage.exists(old_name)


@pytest.mark.django_db
def test_private_document_create_cleans_file_when_audit_fails(django_user_model, monkeypatch):
    _, branches, perm_manage, *_ = _context(django_user_model)
    manager = _branch_user(django_user_model, branch=branches[0], perms=[perm_manage])

    from apps.documents.forms import PrivateDocumentForm

    form = PrivateDocumentForm(
        data={
            "title": "Contrato fallido",
            "document_type": PrivateDocument.DocumentType.CONTRACT,
            "branch": branches[0].pk,
            "status": PrivateDocument.Status.ACTIVE,
            "is_confidential": True,
        },
        files={"file": SimpleUploadedFile("fallido.pdf", b"%PDF-1.4 failed", content_type="application/pdf")},
        user=manager,
    )
    assert form.is_valid(), form.errors

    def fail_audit(**kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr("apps.documents.services.audit_log", fail_audit)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        create_private_document(actor=manager, form=form)

    assert not form.instance.file.storage.exists(form.instance.file.name)
    assert not PrivateDocument.objects.filter(title="Contrato fallido").exists()


@pytest.mark.django_db
def test_private_document_replacement_removes_old_file_after_commit(
    django_user_model,
    django_capture_on_commit_callbacks,
):
    _, branches, perm_manage, *_ = _context(django_user_model)
    manager = _branch_user(django_user_model, branch=branches[0], perms=[perm_manage])
    document = _private_document(branch=branches[0], user=manager, filename="original.pdf")
    old_name = document.file.name
    storage = document.file.storage
    form = _private_document_update_form(document=document, user=manager, filename="nuevo.pdf")

    with django_capture_on_commit_callbacks(execute=True):
        updated = update_private_document(actor=manager, document=document, form=form)

    assert updated.file.name != old_name
    assert storage.exists(updated.file.name)
    assert not storage.exists(old_name)


@pytest.mark.django_db
def test_private_document_replacement_failure_keeps_old_and_cleans_new(
    django_user_model,
    monkeypatch,
):
    _, branches, perm_manage, *_ = _context(django_user_model)
    manager = _branch_user(django_user_model, branch=branches[0], perms=[perm_manage])
    document = _private_document(branch=branches[0], user=manager, filename="original-failure.pdf")
    old_name = document.file.name
    storage = document.file.storage
    form = _private_document_update_form(document=document, user=manager, filename="fallo-reemplazo.pdf")

    def fail_audit(**kwargs):
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr("apps.documents.services.audit_log", fail_audit)
    with pytest.raises(RuntimeError, match="audit unavailable"):
        update_private_document(actor=manager, document=document, form=form)
    failed_name = document.file.name

    document.refresh_from_db()
    assert document.file.name == old_name
    assert storage.exists(old_name)
    assert not storage.exists(failed_name)


@pytest.mark.django_db
def test_selector_scope_for_branch_user(django_user_model):
    company, branches, perm_manage, *_ = _context(django_user_model)
    manager_a = _branch_user(django_user_model, branch=branches[0], perms=[perm_manage], code="mgr_a")
    qs = private_documents_queryset(user=manager_a)
    assert set(qs.values_list("branch_id", flat=True)) <= {branches[0].pk}
    assert allowed_document_branch_ids(manager_a) == {branches[0].pk}


@pytest.mark.django_db
def test_register_download_records_audit_and_timestamp(django_user_model):
    company, branches, perm_manage, *_ = _context(django_user_model)
    manager = _branch_user(django_user_model, branch=branches[0], perms=[perm_manage])
    doc = _private_document(branch=branches[0], user=manager)
    assert doc.last_downloaded_at is None
    register_document_download(actor=manager, document=doc)
    doc.refresh_from_db()
    assert doc.last_downloaded_at is not None


@pytest.mark.django_db
def test_archived_document_hidden_and_blocked(django_user_model, client):
    company, branches, _, perm_manage, perm_download = _context(django_user_model)
    manager = _branch_user(django_user_model, branch=branches[0], perms=[perm_manage, perm_download])
    doc = _private_document(branch=branches[0], user=manager)
    archive_private_document(actor=manager, document=doc)
    client.force_login(manager)
    assert client.get(f"/dashboard/documents/{doc.pk}/download/").status_code == 404
    assert not private_documents_queryset(user=manager).filter(pk=doc.pk).exists()


@pytest.mark.django_db
def test_download_view_sets_safety_headers(django_user_model, client):
    company, branches, perm_manage, *_ = _context(django_user_model)
    admin = _superuser(django_user_model)
    manager = _branch_user(django_user_model, branch=branches[0], perms=[perm_manage])
    doc = _private_document(branch=branches[0], user=manager)
    client.force_login(admin)
    resp = client.get(f"/dashboard/documents/{doc.pk}/download/")
    assert resp["Cache-Control"] == "private, no-store, max-age=0"
    assert resp["Pragma"] == "no-cache"
