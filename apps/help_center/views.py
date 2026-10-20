"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de ayuda.

EN: This module orchestrates HTTP requests, permissions, and responses for the help center domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the help center domain.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import ListView, TemplateView

from apps.help_center.forms import HelpArticleForm, HelpSearchForm
from apps.help_center.models import HelpArticle, HelpArticleVersion, HelpChecklistItem
from apps.help_center.selectors import (
    checklist_progress,
    resource_visible_to_user,
    visible_articles_for_user,
    visible_checklists_for_user,
)
from apps.help_center.services import (
    create_help_article,
    restore_help_article_version,
    set_help_article_publication,
    set_training_mode,
    toggle_checklist_item,
    update_help_article,
)


class HelpAccessMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.can_view_help:
            raise PermissionDenied("No tienes acceso al centro de ayuda.")
        return super().dispatch(request, *args, **kwargs)


class HelpManageMixin(LoginRequiredMixin):
    """ES: Exige `help.manage`; ser Staff por sí solo no concede acceso.

    EN: Requires `help.manage`; Staff status alone never grants access.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.can_manage_help:
            raise PermissionDenied("No tienes permiso para gestionar contenido de ayuda.")
        return super().dispatch(request, *args, **kwargs)


class HelpHomeView(HelpAccessMixin, TemplateView):
    template_name = "help_center/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        articles = visible_articles_for_user(self.request.user)
        checklists = visible_checklists_for_user(self.request.user)
        categories = {}
        for article in articles:
            categories.setdefault(article.category, []).append(article)
        context.update(
            {
                "featured_articles": [article for article in articles if article.is_featured][:6],
                "article_categories": list(categories.items()),
                "checklist_cards": [checklist_progress(checklist, self.request.user) for checklist in checklists],
                "search_form": HelpSearchForm(),
            }
        )
        return context


class HelpSearchView(HelpAccessMixin, TemplateView):
    template_name = "help_center/search.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        form = HelpSearchForm(self.request.GET)
        query = ""
        results = []
        if form.is_valid():
            query = form.cleaned_data["q"].strip()
            if query:
                results = visible_articles_for_user(self.request.user, query=query)
        context.update({"form": form, "query": query, "results": results})
        return context


class ArticleMixin(HelpAccessMixin):
    def get_article(self):
        slug = self.kwargs["slug"]
        article = next(
            (item for item in visible_articles_for_user(self.request.user) if item.slug == slug),
            None,
        )
        if not article:
            raise Http404("Artículo no encontrado.")
        return article


class HelpArticleDetailView(ArticleMixin, TemplateView):
    template_name = "help_center/article_detail.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["article"] = self.get_article()
        return context


class HelpArticlePrintView(ArticleMixin, TemplateView):
    template_name = "help_center/article_print.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["article"] = self.get_article()
        return context


class HelpChecklistDetailView(HelpAccessMixin, TemplateView):
    template_name = "help_center/checklist_detail.html"

    def get_checklist(self):
        slug = self.kwargs["slug"]
        checklist = next(
            (item for item in visible_checklists_for_user(self.request.user) if item.slug == slug),
            None,
        )
        if not checklist:
            raise Http404("Checklist no encontrado.")
        return checklist

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(checklist_progress(self.get_checklist(), self.request.user))
        return context


class ToggleChecklistItemView(HelpAccessMixin, View):
    def post(self, request, item_id, *args, **kwargs):
        item = HelpChecklistItem.objects.select_related("checklist").filter(pk=item_id).first()
        if not item or not item.checklist.is_published or not resource_visible_to_user(item.checklist, request.user):
            raise Http404("Paso de checklist no encontrado.")
        completed = toggle_checklist_item(user=request.user, item=item)
        messages.success(request, "Paso marcado como completado." if completed else "Paso marcado como pendiente.")
        return redirect(reverse("help_center:checklist", kwargs={"slug": item.checklist.slug}))


class ToggleTrainingModeView(HelpAccessMixin, View):
    def post(self, request, *args, **kwargs):
        enabled = request.POST.get("enabled") == "1"
        set_training_mode(user=request.user, enabled=enabled)
        messages.success(
            request,
            "Modo capacitación activado." if enabled else "Modo capacitación desactivado.",
        )
        next_url = request.POST.get("next", "")
        if not url_has_allowed_host_and_scheme(
            next_url,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            next_url = reverse("help_center:home")
        return redirect(next_url)


class HelpArticleManageListView(HelpManageMixin, ListView):
    template_name = "help_center/manage/article_list.html"
    context_object_name = "articles"
    paginate_by = 30

    def get_queryset(self):
        return HelpArticle.objects.select_related("category", "updated_by").order_by(
            "category__order", "order", "title"
        )


class HelpArticleManageFormView(HelpManageMixin, View):
    template_name = "help_center/manage/article_form.html"

    def get_article(self):
        pk = self.kwargs.get("pk")
        return get_object_or_404(HelpArticle, pk=pk) if pk else None

    def render_form(self, request, form, article):
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "article": article,
                "page_heading": "Editar artículo" if article else "Crear artículo",
            },
        )

    def get(self, request, pk=None):
        article = self.get_article()
        return self.render_form(request, HelpArticleForm(instance=article), article)

    def post(self, request, pk=None):
        article = self.get_article()
        form = HelpArticleForm(request.POST, instance=article)
        if form.is_valid():
            if article:
                article = update_help_article(actor=request.user, article=article, form=form)
            else:
                article = create_help_article(actor=request.user, form=form)
            messages.success(request, "Artículo y versión guardados correctamente.")
            return redirect("help_center:manage_preview", pk=article.pk)
        return self.render_form(request, form, article)


class HelpArticleManagePreviewView(HelpManageMixin, TemplateView):
    template_name = "help_center/manage/article_preview.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["article"] = get_object_or_404(
            HelpArticle.objects.select_related("category", "updated_by"), pk=self.kwargs["pk"]
        )
        return context


class HelpArticlePublicationView(HelpManageMixin, View):
    def post(self, request, pk, action):
        article = get_object_or_404(HelpArticle, pk=pk)
        if action not in {"publish", "unpublish"}:
            raise Http404("Acción de publicación no encontrada.")
        set_help_article_publication(
            actor=request.user,
            article=article,
            published=action == "publish",
        )
        messages.success(request, "Estado de publicación actualizado.")
        return redirect("help_center:manage_preview", pk=article.pk)


class HelpArticleHistoryView(HelpManageMixin, ListView):
    template_name = "help_center/manage/article_history.html"
    context_object_name = "versions"
    paginate_by = 30

    def dispatch(self, request, *args, **kwargs):
        self.article = get_object_or_404(HelpArticle, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return self.article.versions.select_related("created_by", "category")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["article"] = self.article
        return context


class HelpArticleRestoreView(HelpManageMixin, View):
    def post(self, request, pk, version_pk):
        article = get_object_or_404(HelpArticle, pk=pk)
        version = get_object_or_404(HelpArticleVersion, pk=version_pk, article=article)
        restore_help_article_version(actor=request.user, article=article, version=version)
        messages.success(request, f"Versión {version.version} restaurada como una versión nueva.")
        return redirect("help_center:manage_history", pk=article.pk)
