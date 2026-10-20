"""ES: Este módulo define modelos persistentes, estados y restricciones para el dominio de ayuda.

EN: This module defines persistent models, states, and constraints for the help center domain.

Contexto existente / Existing context:
Persistent domain models and database constraints for the help center domain.
"""

from __future__ import annotations

from django.conf import settings
from django.db import models

from apps.common.models import TimeStampedModel


class HelpCategory(TimeStampedModel):
    name = models.CharField(max_length=120)
    slug = models.SlugField(max_length=120, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=12, blank=True)
    order = models.PositiveSmallIntegerField(default=50, db_index=True)
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["order", "name"]
        verbose_name = "Categoría de ayuda"
        verbose_name_plural = "Categorías de ayuda"

    def __str__(self):
        return self.name


class HelpArticle(TimeStampedModel):
    class ArticleType(models.TextChoices):
        GUIDE = "guide", "Guía"
        MANUAL = "manual", "Manual"
        CONTEXT = "context", "Ayuda contextual"
        FAQ = "faq", "Pregunta frecuente"

    category = models.ForeignKey(HelpCategory, on_delete=models.PROTECT, related_name="articles")
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=180, unique=True)
    summary = models.TextField(blank=True)
    content = models.TextField()
    article_type = models.CharField(max_length=20, choices=ArticleType.choices, default=ArticleType.GUIDE, db_index=True)
    route_name = models.CharField(
        max_length=180,
        blank=True,
        db_index=True,
        help_text="Nombre de URL de Django al que se asocia la ayuda contextual.",
    )
    permission_code = models.CharField(max_length=120, blank=True, db_index=True)
    role_codes = models.JSONField(default=list, blank=True)
    keywords = models.CharField(max_length=500, blank=True)
    estimated_minutes = models.PositiveSmallIntegerField(default=5)
    order = models.PositiveSmallIntegerField(default=50, db_index=True)
    is_featured = models.BooleanField(default=False, db_index=True)
    is_published = models.BooleanField(default=True, db_index=True)
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="help_articles_updated",
    )

    class Meta:
        ordering = ["category__order", "order", "title"]
        indexes = [
            models.Index(fields=["is_published", "article_type", "order"]),
            models.Index(fields=["route_name", "is_published"]),
        ]
        verbose_name = "Artículo de ayuda"
        verbose_name_plural = "Artículos de ayuda"

    def __str__(self):
        return self.title


class HelpArticleVersion(TimeStampedModel):
    """ES: Instantánea inmutable de una versión publicada o editada.

    EN: Immutable snapshot of an edited or published article version.
    """

    article = models.ForeignKey(HelpArticle, on_delete=models.CASCADE, related_name="versions")
    version = models.PositiveIntegerField()
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=180)
    summary = models.TextField(blank=True)
    content = models.TextField()
    article_type = models.CharField(max_length=20, choices=HelpArticle.ArticleType.choices)
    category = models.ForeignKey(HelpCategory, on_delete=models.PROTECT, related_name="article_versions")
    route_name = models.CharField(max_length=180, blank=True)
    permission_code = models.CharField(max_length=120, blank=True)
    role_codes = models.JSONField(default=list, blank=True)
    keywords = models.CharField(max_length=500, blank=True)
    estimated_minutes = models.PositiveSmallIntegerField(default=5)
    order = models.PositiveSmallIntegerField(default=50)
    is_featured = models.BooleanField(default=False)
    is_published = models.BooleanField(default=False)
    change_note = models.CharField(max_length=220, blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="help_article_versions_created",
    )

    class Meta:
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(fields=["article", "version"], name="unique_help_article_version"),
        ]
        verbose_name = "Versión de artículo de ayuda"
        verbose_name_plural = "Versiones de artículos de ayuda"

    def __str__(self):
        return f"{self.article} · v{self.version}"


class HelpChecklist(TimeStampedModel):
    title = models.CharField(max_length=180)
    slug = models.SlugField(max_length=180, unique=True)
    summary = models.TextField(blank=True)
    permission_code = models.CharField(max_length=120, blank=True, db_index=True)
    role_codes = models.JSONField(default=list, blank=True)
    order = models.PositiveSmallIntegerField(default=50, db_index=True)
    is_published = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["order", "title"]
        verbose_name = "Checklist de ayuda"
        verbose_name_plural = "Checklists de ayuda"

    def __str__(self):
        return self.title


class HelpChecklistItem(TimeStampedModel):
    checklist = models.ForeignKey(HelpChecklist, on_delete=models.CASCADE, related_name="items")
    title = models.CharField(max_length=180)
    instructions = models.TextField(blank=True)
    route_name = models.CharField(max_length=180, blank=True)
    order = models.PositiveSmallIntegerField(default=50)
    is_required = models.BooleanField(default=True)

    class Meta:
        ordering = ["order", "id"]
        constraints = [
            models.UniqueConstraint(fields=["checklist", "order"], name="unique_help_checklist_item_order"),
        ]
        verbose_name = "Paso de checklist"
        verbose_name_plural = "Pasos de checklist"

    def __str__(self):
        return f"{self.checklist}: {self.title}"


class UserChecklistProgress(TimeStampedModel):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="help_progress")
    item = models.ForeignKey(HelpChecklistItem, on_delete=models.CASCADE, related_name="user_progress")
    completed_at = models.DateTimeField()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "item"], name="unique_user_help_item_progress"),
        ]
        indexes = [models.Index(fields=["user", "completed_at"])]
        verbose_name = "Progreso de capacitación"
        verbose_name_plural = "Progreso de capacitación"

    def __str__(self):
        return f"{self.user} - {self.item}"


class UserHelpPreference(TimeStampedModel):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="help_preference")
    training_mode = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Preferencia de ayuda"
        verbose_name_plural = "Preferencias de ayuda"

    def __str__(self):
        return f"Ayuda de {self.user}"
