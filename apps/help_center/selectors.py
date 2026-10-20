"""ES: Este módulo implementa consultas de lectura conscientes de autorización para el dominio de ayuda.

EN: This module implements authorization-aware read queries for the help center domain.

Contexto existente / Existing context:
Read queries and authorization-aware selectors for the help center domain.
"""

from __future__ import annotations

from django.db.models import Q

from apps.help_center.models import HelpArticle, HelpChecklist, UserChecklistProgress, UserHelpPreference


def _role_codes(user) -> set[str]:
    return set(user.role_codes()) if user.is_authenticated else set()


def resource_visible_to_user(resource, user) -> bool:
    if not user.is_authenticated or not user.can_view_help:
        return False
    if user.is_superuser:
        return True
    permission_code = (resource.permission_code or "").strip()
    if permission_code and not user.has_perm_code(permission_code):
        return False
    allowed_roles = set(resource.role_codes or [])
    if allowed_roles and not allowed_roles.intersection(_role_codes(user)):
        return False
    return True


def visible_articles_for_user(user, *, query: str = "") -> list[HelpArticle]:
    queryset = HelpArticle.objects.filter(is_published=True, category__is_active=True).select_related("category")
    query = query.strip()
    if query:
        queryset = queryset.filter(
            Q(title__icontains=query)
            | Q(summary__icontains=query)
            | Q(content__icontains=query)
            | Q(keywords__icontains=query)
            | Q(category__name__icontains=query)
        )
    return [article for article in queryset if resource_visible_to_user(article, user)]


def visible_checklists_for_user(user) -> list[HelpChecklist]:
    queryset = HelpChecklist.objects.filter(is_published=True).prefetch_related("items")
    return [checklist for checklist in queryset if resource_visible_to_user(checklist, user)]


def contextual_article_for_user(user, route_name: str) -> HelpArticle | None:
    if not route_name:
        return None
    candidates = HelpArticle.objects.filter(
        is_published=True,
        category__is_active=True,
        route_name=route_name,
    ).select_related("category")
    return next((article for article in candidates if resource_visible_to_user(article, user)), None)


def training_mode_for_user(user) -> bool:
    if not user.is_authenticated:
        return False
    preference = UserHelpPreference.objects.filter(user=user).only("training_mode").first()
    return bool(preference and preference.training_mode)


def checklist_progress(checklist: HelpChecklist, user) -> dict:
    items = list(checklist.items.all())
    completed_ids = set(
        UserChecklistProgress.objects.filter(user=user, item__checklist=checklist).values_list("item_id", flat=True)
    )
    completed = len(completed_ids)
    total = len(items)
    percent = round((completed / total) * 100) if total else 0
    return {
        "checklist": checklist,
        "items": items,
        "completed_ids": completed_ids,
        "completed": completed,
        "total": total,
        "percent": percent,
    }
