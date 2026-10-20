"""ES: Este módulo implementa servicios de negocio y efectos transaccionales para el dominio de ayuda.

EN: This module implements business services and transactional effects for the help center domain.

Contexto existente / Existing context:
Transactional business services for the help center domain.
"""

from __future__ import annotations

from django.db import transaction
from django.utils import timezone

from apps.audit.services import audit_log
from apps.help_center.models import (
    HelpArticle,
    HelpArticleVersion,
    HelpChecklistItem,
    UserChecklistProgress,
    UserHelpPreference,
)


ARTICLE_EDITABLE_FIELDS = (
    "category", "title", "slug", "summary", "content", "article_type",
    "route_name", "permission_code", "role_codes", "keywords",
    "estimated_minutes", "order", "is_featured", "is_published",
)


def _article_snapshot(article: HelpArticle) -> dict:
    """ES: Devuelve una instantánea serializable y sin contenido oculto.

    EN: Returns a serializable snapshot without hidden content.
    """

    return {
        "category": article.category_id,
        "title": article.title,
        "slug": article.slug,
        "summary": article.summary,
        "content": article.content,
        "article_type": article.article_type,
        "route_name": article.route_name,
        "permission_code": article.permission_code,
        "role_codes": list(article.role_codes or []),
        "keywords": article.keywords,
        "estimated_minutes": article.estimated_minutes,
        "order": article.order,
        "is_featured": article.is_featured,
        "is_published": article.is_published,
    }


def _record_article_version(*, article: HelpArticle, actor, change_note: str) -> HelpArticleVersion:
    latest = article.versions.select_for_update().order_by("-version").first()
    snapshot = _article_snapshot(article)
    snapshot["category_id"] = snapshot.pop("category")
    return HelpArticleVersion.objects.create(
        article=article,
        version=(latest.version + 1) if latest else 1,
        created_by=actor if getattr(actor, "is_authenticated", False) else None,
        change_note=change_note,
        **snapshot,
    )


@transaction.atomic
def create_help_article(*, actor, form) -> HelpArticle:
    """ES: Crea un artículo y su primera versión auditable.

    EN: Creates an article and its first auditable version.
    """

    article = HelpArticle(updated_by=actor)
    for field in ARTICLE_EDITABLE_FIELDS:
        setattr(article, field, form.cleaned_data[field])
    article.full_clean()
    article.save()
    version = _record_article_version(
        article=article,
        actor=actor,
        change_note=form.cleaned_data["change_note"],
    )
    audit_log(
        user=actor,
        action="help.article.create",
        target=article,
        after={"version": version.version, "published": article.is_published},
    )
    return article


@transaction.atomic
def update_help_article(*, actor, article: HelpArticle, form) -> HelpArticle:
    """ES: Actualiza bajo bloqueo y registra una versión completa.

    EN: Updates under a row lock and records a complete version.
    """

    article = HelpArticle.objects.select_for_update().get(pk=article.pk)
    before = _article_snapshot(article)
    for field in ARTICLE_EDITABLE_FIELDS:
        setattr(article, field, form.cleaned_data[field])
    article.updated_by = actor
    article.full_clean()
    article.save()
    version = _record_article_version(
        article=article,
        actor=actor,
        change_note=form.cleaned_data["change_note"],
    )
    audit_log(
        user=actor,
        action="help.article.update",
        target=article,
        before={"version": version.version - 1, "published": before["is_published"]},
        after={"version": version.version, "published": article.is_published},
    )
    return article


@transaction.atomic
def set_help_article_publication(*, actor, article: HelpArticle, published: bool) -> HelpArticle:
    """ES: Publica o despublica explícitamente y crea una versión.

    EN: Explicitly publishes or unpublishes and creates a version.
    """

    article = HelpArticle.objects.select_for_update().get(pk=article.pk)
    before = article.is_published
    if before == published:
        return article
    article.is_published = published
    article.updated_by = actor
    article.save(update_fields=["is_published", "updated_by", "updated_at"])
    version = _record_article_version(
        article=article,
        actor=actor,
        change_note="Publicación" if published else "Despublicación",
    )
    audit_log(
        user=actor,
        action="help.article.publish" if published else "help.article.unpublish",
        target=article,
        before={"published": before},
        after={"published": published, "version": version.version},
    )
    return article


@transaction.atomic
def restore_help_article_version(
    *, actor, article: HelpArticle, version: HelpArticleVersion
) -> HelpArticle:
    """ES: Restaura una instantánea y conserva el historial previo.

    EN: Restores a snapshot while preserving prior history.
    """

    article = HelpArticle.objects.select_for_update().get(pk=article.pk)
    version = HelpArticleVersion.objects.select_for_update().get(pk=version.pk, article=article)
    before = _article_snapshot(article)
    for field in ARTICLE_EDITABLE_FIELDS:
        value = version.category if field == "category" else getattr(version, field)
        setattr(article, field, value)
    article.updated_by = actor
    article.full_clean()
    article.save()
    restored = _record_article_version(
        article=article,
        actor=actor,
        change_note=f"Restauración de la versión {version.version}",
    )
    audit_log(
        user=actor,
        action="help.article.restore",
        target=article,
        before={"version": restored.version - 1, "published": before["is_published"]},
        after={"version": restored.version, "restored_from": version.version, "published": article.is_published},
    )
    return article


@transaction.atomic
def set_training_mode(*, user, enabled: bool) -> UserHelpPreference:
    preference, _ = UserHelpPreference.objects.select_for_update().get_or_create(user=user)
    previous = preference.training_mode
    preference.training_mode = enabled
    preference.save(update_fields=["training_mode", "updated_at"])
    audit_log(
        user=user,
        action="help.training_mode.updated",
        target=preference,
        before={"training_mode": previous},
        after={"training_mode": enabled},
    )
    return preference


@transaction.atomic
def toggle_checklist_item(*, user, item: HelpChecklistItem) -> bool:
    progress = UserChecklistProgress.objects.select_for_update().filter(user=user, item=item).first()
    if progress:
        progress.delete()
        completed = False
    else:
        UserChecklistProgress.objects.create(user=user, item=item, completed_at=timezone.now())
        completed = True
    audit_log(
        user=user,
        action="help.checklist.updated",
        target=item.checklist,
        after={"item_id": item.pk, "item": item.title, "completed": completed},
    )
    return completed
