"""ES: Este módulo implementa servicios de negocio y efectos transaccionales para el dominio de documentos.

EN: This module implements business services and transactional effects for the documents domain.

Contexto existente / Existing context:
Transactional business services for the documents domain.
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from django.db import transaction
from django.utils import timezone

from apps.audit.services import audit_log
from apps.documents.models import DocumentCategory, PrivateDocument, ReusableAsset

logger = logging.getLogger(__name__)


def _delete_storage_object(storage, name: str, *, context: str) -> None:
    """Best-effort cleanup without exposing provider details or credentials."""
    if not name:
        return
    try:
        storage.delete(name)
    except Exception as exc:  # noqa: BLE001 - cleanup must not mask the original operation
        logger.warning("No se pudo limpiar un archivo de %s (%s).", context, exc.__class__.__name__)


def _cleanup_replaced_file(*, storage, old_name: str, new_name: str, context: str) -> None:
    if old_name and old_name != new_name:
        transaction.on_commit(lambda: _delete_storage_object(storage, old_name, context=context))


def _uploaded_file_metadata(uploaded_file):
    """Return safe metadata and a sha256 hash without trusting user input."""
    if not uploaded_file:
        return {"file_hash": "", "original_name": "", "mime_type": "", "size_bytes": 0, "extension": ""}
    position = uploaded_file.tell() if hasattr(uploaded_file, "tell") else None
    try:
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)
        digest = hashlib.sha256()
        for chunk in uploaded_file.chunks():
            digest.update(chunk)
        if hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)
    finally:
        if position is not None and hasattr(uploaded_file, "seek"):
            uploaded_file.seek(0)
    return {
        "file_hash": digest.hexdigest(),
        "original_name": Path(uploaded_file.name).name[:220],
        "mime_type": getattr(uploaded_file, "content_type", "") or "",
        "size_bytes": getattr(uploaded_file, "size", 0) or 0,
        "extension": Path(uploaded_file.name).suffix.lower()[:20],
    }


def _asset_snapshot(asset: ReusableAsset):
    return {
        "title": asset.title,
        "asset_type": asset.asset_type,
        "visibility": asset.visibility,
        "branch_id": asset.branch_id,
        "vehicle_model_id": asset.vehicle_model_id,
        "vehicle_year": asset.vehicle_year,
        "is_active": asset.is_active,
        "file_hash": asset.file_hash,
        "size_bytes": asset.size_bytes,
    }


def _document_snapshot(document: PrivateDocument):
    return {
        "title": document.title,
        "document_type": document.document_type,
        "status": document.status,
        "branch_id": document.branch_id,
        "customer_id": document.customer_id,
        "vehicle_id": document.vehicle_id,
        "sale_id": document.sale_id,
        "is_confidential": document.is_confidential,
        "file_hash": document.file_hash,
        "size_bytes": document.size_bytes,
    }


@transaction.atomic
def create_reusable_asset(*, actor, form) -> ReusableAsset:
    asset = form.save(commit=False)
    metadata = _uploaded_file_metadata(form.cleaned_data.get("file"))
    for key, value in metadata.items():
        setattr(asset, key, value)
    asset.uploaded_by = actor if getattr(actor, "is_authenticated", False) else None
    try:
        asset.save()
        audit_log(user=actor, action="documents.asset.create", target=asset, after=_asset_snapshot(asset))
    except Exception:
        _delete_storage_object(asset.file.storage, asset.file.name, context="recurso nuevo")
        raise
    return asset


@transaction.atomic
def update_reusable_asset(*, actor, asset: ReusableAsset, form) -> ReusableAsset:
    persisted = ReusableAsset.objects.select_for_update().get(pk=asset.pk)
    before = _asset_snapshot(persisted)
    old_name = persisted.file.name
    old_storage = persisted.file.storage
    asset = form.save(commit=False)
    replacement = form.cleaned_data.get("file") if "file" in form.changed_data else None
    if replacement:
        metadata = _uploaded_file_metadata(form.cleaned_data.get("file"))
        for key, value in metadata.items():
            setattr(asset, key, value)
    try:
        asset.save()
        audit_log(
            user=actor, action="documents.asset.update", target=asset, before=before, after=_asset_snapshot(asset)
        )
    except Exception:
        if replacement and asset.file.name != old_name:
            _delete_storage_object(asset.file.storage, asset.file.name, context="recurso reemplazado")
        raise
    if replacement:
        _cleanup_replaced_file(
            storage=old_storage,
            old_name=old_name,
            new_name=asset.file.name,
            context="recurso anterior",
        )
    return asset


@transaction.atomic
def archive_reusable_asset(*, actor, asset: ReusableAsset) -> ReusableAsset:
    before = _asset_snapshot(asset)
    asset.is_active = False
    asset.soft_delete()
    audit_log(
        user=actor,
        action="documents.asset.archive",
        target=asset,
        before=before,
        after={"is_deleted": True, "is_active": False},
    )
    return asset


@transaction.atomic
def create_private_document(*, actor, form) -> PrivateDocument:
    document = form.save(commit=False)
    metadata = _uploaded_file_metadata(form.cleaned_data.get("file"))
    for key, value in metadata.items():
        setattr(document, key, value)
    document.uploaded_by = actor if getattr(actor, "is_authenticated", False) else None
    try:
        document.save()
        audit_log(user=actor, action="documents.private.create", target=document, after=_document_snapshot(document))
    except Exception:
        _delete_storage_object(document.file.storage, document.file.name, context="documento nuevo")
        raise
    if document.customer_id and document.document_type != PrivateDocument.DocumentType.INVOICE:
        from apps.notifications.services import schedule_customer_event_notification

        try:
            schedule_customer_event_notification(
                customer=document.customer,
                title=f"Nuevo documento: {document.title}",
                body="Se publicó un nuevo documento privado en tu expediente.",
                message_type="document",
                dedup_key=f"document:{document.pk}:published",
                actor=actor,
                branch=document.branch,
                related_vehicle=document.vehicle,
                related_sale=document.sale,
                related_document=document,
            )
        except Exception:
            _delete_storage_object(document.file.storage, document.file.name, context="documento nuevo")
            raise
    return document


@transaction.atomic
def update_private_document(*, actor, document: PrivateDocument, form) -> PrivateDocument:
    persisted = PrivateDocument.objects.select_for_update().get(pk=document.pk)
    before = _document_snapshot(persisted)
    old_name = persisted.file.name
    old_storage = persisted.file.storage
    document = form.save(commit=False)
    replacement = form.cleaned_data.get("file") if "file" in form.changed_data else None
    if replacement:
        metadata = _uploaded_file_metadata(form.cleaned_data.get("file"))
        for key, value in metadata.items():
            setattr(document, key, value)
    try:
        document.save()
        audit_log(
            user=actor,
            action="documents.private.update",
            target=document,
            before=before,
            after=_document_snapshot(document),
        )
    except Exception:
        if replacement and document.file.name != old_name:
            _delete_storage_object(document.file.storage, document.file.name, context="documento reemplazado")
        raise
    if replacement:
        _cleanup_replaced_file(
            storage=old_storage,
            old_name=old_name,
            new_name=document.file.name,
            context="documento anterior",
        )
    return document


@transaction.atomic
def archive_private_document(*, actor, document: PrivateDocument) -> PrivateDocument:
    before = _document_snapshot(document)
    document.status = PrivateDocument.Status.ARCHIVED
    document.is_deleted = True
    document.deleted_at = timezone.now()
    document.save(update_fields=["status", "is_deleted", "deleted_at", "updated_at"])
    audit_log(
        user=actor,
        action="documents.private.archive",
        target=document,
        before=before,
        after={"status": document.status, "is_deleted": True},
    )
    return document


@transaction.atomic
def register_document_download(*, actor, document: PrivateDocument, customer=None) -> PrivateDocument:
    document.last_downloaded_at = timezone.now()
    document.save(update_fields=["last_downloaded_at", "updated_at"])
    audit_log(
        user=actor,
        action="documents.private.download",
        target=document,
        customer=customer,
        metadata={"file_hash": document.file_hash, "size_bytes": document.size_bytes},
    )
    return document


@transaction.atomic
def register_asset_download(*, actor, asset: ReusableAsset, customer=None) -> ReusableAsset:
    audit_log(
        user=actor,
        action="documents.asset.download",
        target=asset,
        customer=customer,
        metadata={"file_hash": asset.file_hash, "size_bytes": asset.size_bytes},
    )
    return asset


@transaction.atomic
def create_document_category(*, actor, form) -> DocumentCategory:
    category = form.save()
    audit_log(
        user=actor,
        action="documents.category.create",
        target=category,
        after={"name": category.name, "scope": category.scope},
    )
    return category
