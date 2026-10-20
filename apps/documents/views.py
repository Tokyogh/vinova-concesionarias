"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de documentos.

EN: This module orchestrates HTTP requests, permissions, and responses for the documents domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the documents domain.
"""

from __future__ import annotations

import logging
from pathlib import Path

from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from apps.accounts.views import PermissionCodeRequiredMixin
from apps.documents.forms import AssetSearchForm, DocumentCategoryForm, DocumentSearchForm, PrivateDocumentForm, ReusableAssetForm
from apps.documents.models import PrivateDocument, ReusableAsset
from apps.documents.selectors import (
    document_dashboard_metrics,
    document_categories_queryset,
    private_documents_queryset,
    recent_assets,
    recent_documents,
    reusable_assets_queryset,
)
from apps.documents.services import (
    archive_private_document,
    archive_reusable_asset,
    create_document_category,
    create_private_document,
    create_reusable_asset,
    register_document_download,
    update_private_document,
    update_reusable_asset,
)

logger = logging.getLogger(__name__)


class DocumentLibraryView(PermissionCodeRequiredMixin, ListView):
    permission_code = "documents.view"
    template_name = "documents/internal/document_list.html"
    context_object_name = "documents"
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.has_perm_code("documents.view") and request.user.has_perm_code("documents.manage"):
            self.permission_code = "documents.manage"
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        self.search_form = DocumentSearchForm(self.request.GET, user=self.request.user)
        query = document_type = status = sort = ""
        branch = None
        if self.search_form.is_valid():
            query = self.search_form.cleaned_data.get("q", "")
            document_type = self.search_form.cleaned_data.get("document_type", "")
            status = self.search_form.cleaned_data.get("status", "")
            branch = self.search_form.cleaned_data.get("branch")
            sort = self.search_form.cleaned_data.get("sort", "")
        return private_documents_queryset(query=query, document_type=document_type, status=status, branch=branch, user=self.request.user, sort=sort)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_form"] = self.search_form
        ctx["metrics"] = document_dashboard_metrics(user=self.request.user)
        ctx["recent_assets"] = recent_assets(5, user=self.request.user)
        return ctx


class PrivateDocumentCreateView(PermissionCodeRequiredMixin, CreateView):
    permission_code = "documents.manage"
    model = PrivateDocument
    form_class = PrivateDocumentForm
    template_name = "documents/internal/document_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            self.object = create_private_document(actor=self.request.user, form=form)
        except Exception as exc:  # noqa: BLE001 - fallo externo controlado y sin detalles sensibles
            logger.warning("Falló el almacenamiento del documento privado (%s).", exc.__class__.__name__)
            messages.error(self.request, "No se pudo almacenar el documento. Inténtalo nuevamente más tarde.")
            return self.form_invalid(form)
        messages.success(self.request, "Documento privado cargado correctamente.")
        return redirect("documents_internal:detail", pk=self.object.pk)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_heading"] = "Cargar documento privado"
        ctx["mode"] = "create"
        return ctx


class PrivateDocumentDetailView(PermissionCodeRequiredMixin, DetailView):
    permission_code = "documents.view"
    template_name = "documents/internal/document_detail.html"
    context_object_name = "document"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.has_perm_code("documents.view") and request.user.has_perm_code("documents.manage"):
            self.permission_code = "documents.manage"
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return private_documents_queryset(user=self.request.user)


class PrivateDocumentUpdateView(PermissionCodeRequiredMixin, DetailView):
    permission_code = "documents.manage"
    template_name = "documents/internal/document_form.html"
    context_object_name = "document"

    def get_queryset(self):
        return private_documents_queryset(user=self.request.user)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = PrivateDocumentForm(instance=self.object, user=request.user)
        return self.render_to_response(self.get_context_data(form=form, mode="update", page_heading="Editar documento privado"))

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = PrivateDocumentForm(request.POST, request.FILES, instance=self.object, user=request.user)
        if form.is_valid():
            try:
                self.object = update_private_document(actor=request.user, document=self.object, form=form)
            except Exception as exc:  # noqa: BLE001 - fallo externo controlado y sin detalles sensibles
                logger.warning("Falló el almacenamiento del documento privado (%s).", exc.__class__.__name__)
                messages.error(request, "No se pudo almacenar el documento. Inténtalo nuevamente más tarde.")
                return self.render_to_response(
                    self.get_context_data(form=form, mode="update", page_heading="Editar documento privado")
                )
            messages.success(request, "Documento actualizado correctamente.")
            return redirect("documents_internal:detail", pk=self.object.pk)
        return self.render_to_response(self.get_context_data(form=form, mode="update", page_heading="Editar documento privado"))


class PrivateDocumentDownloadView(PermissionCodeRequiredMixin, View):
    permission_code = "documents.download_private"

    def get(self, request, pk):
        document = get_object_or_404(private_documents_queryset(user=request.user), pk=pk)
        if not document.file:
            raise Http404("El documento no tiene archivo asociado.")
        try:
            handle = document.file.open("rb")
        except Exception as exc:  # noqa: BLE001 - fallo externo controlado y sin detalles sensibles
            logger.warning("Falló la lectura del documento privado (%s).", exc.__class__.__name__)
            messages.error(request, "El archivo no está disponible temporalmente. Inténtalo nuevamente más tarde.")
            return redirect("documents_internal:detail", pk=document.pk)
        register_document_download(actor=request.user, document=document)
        filename = document.original_name or Path(document.file.name).name
        response = FileResponse(handle, as_attachment=True, filename=filename)
        if document.mime_type:
            response["Content-Type"] = document.mime_type
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, no-store, max-age=0"
        response["Pragma"] = "no-cache"
        return response


class PrivateDocumentArchiveView(PermissionCodeRequiredMixin, View):
    permission_code = "documents.manage"

    def post(self, request, pk):
        document = get_object_or_404(private_documents_queryset(user=request.user), pk=pk)
        archive_private_document(actor=request.user, document=document)
        messages.success(request, "Documento archivado correctamente.")
        return redirect("documents_internal:list")


class AssetLibraryView(PermissionCodeRequiredMixin, ListView):
    permission_code = "documents.view"
    template_name = "documents/internal/asset_list.html"
    context_object_name = "assets"
    paginate_by = 24

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.has_perm_code("documents.view") and request.user.has_perm_code("documents.manage"):
            self.permission_code = "documents.manage"
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        self.search_form = AssetSearchForm(self.request.GET)
        query = asset_type = visibility = ""
        if self.search_form.is_valid():
            query = self.search_form.cleaned_data.get("q", "")
            asset_type = self.search_form.cleaned_data.get("asset_type", "")
            visibility = self.search_form.cleaned_data.get("visibility", "")
        return reusable_assets_queryset(query=query, asset_type=asset_type, visibility=visibility, user=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_form"] = self.search_form
        ctx["metrics"] = document_dashboard_metrics(user=self.request.user)
        ctx["recent_documents"] = recent_documents(5, user=self.request.user)
        return ctx


class ReusableAssetCreateView(PermissionCodeRequiredMixin, CreateView):
    permission_code = "documents.manage"
    model = ReusableAsset
    form_class = ReusableAssetForm
    template_name = "documents/internal/asset_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        self.object = create_reusable_asset(actor=self.request.user, form=form)
        messages.success(self.request, "Recurso reutilizable cargado correctamente.")
        return redirect("documents_internal:asset_detail", pk=self.object.pk)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_heading"] = "Cargar recurso reutilizable"
        ctx["mode"] = "create"
        return ctx


class ReusableAssetDetailView(PermissionCodeRequiredMixin, DetailView):
    permission_code = "documents.view"
    template_name = "documents/internal/asset_detail.html"
    context_object_name = "asset"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.has_perm_code("documents.view") and request.user.has_perm_code("documents.manage"):
            self.permission_code = "documents.manage"
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return reusable_assets_queryset(user=self.request.user)


class ReusableAssetUpdateView(PermissionCodeRequiredMixin, DetailView):
    permission_code = "documents.manage"
    template_name = "documents/internal/asset_form.html"
    context_object_name = "asset"

    def get_queryset(self):
        return reusable_assets_queryset(user=self.request.user)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = ReusableAssetForm(instance=self.object, user=request.user)
        return self.render_to_response(self.get_context_data(form=form, mode="update", page_heading="Editar recurso reutilizable"))

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = ReusableAssetForm(request.POST, request.FILES, instance=self.object, user=request.user)
        if form.is_valid():
            self.object = update_reusable_asset(actor=request.user, asset=self.object, form=form)
            messages.success(request, "Recurso actualizado correctamente.")
            return redirect("documents_internal:asset_detail", pk=self.object.pk)
        return self.render_to_response(self.get_context_data(form=form, mode="update", page_heading="Editar recurso reutilizable"))


class ReusableAssetArchiveView(PermissionCodeRequiredMixin, View):
    permission_code = "documents.manage"

    def post(self, request, pk):
        asset = get_object_or_404(reusable_assets_queryset(user=request.user), pk=pk)
        archive_reusable_asset(actor=request.user, asset=asset)
        messages.success(request, "Recurso archivado correctamente.")
        return redirect("documents_internal:assets")


class DocumentCatalogDataView(PermissionCodeRequiredMixin, View):
    permission_code = "documents.manage"
    template_name = "documents/internal/catalog_data.html"

    def get(self, request):
        return self._render(request, DocumentCategoryForm())

    def post(self, request):
        form = DocumentCategoryForm(request.POST)
        if form.is_valid():
            create_document_category(actor=request.user, form=form)
            messages.success(request, "Categoría documental creada correctamente.")
            return redirect("documents_internal:catalog_data")
        messages.error(request, "No se pudo crear la categoría. Revisa los datos.")
        return self._render(request, form)

    def _render(self, request, form):
        from django.shortcuts import render
        return render(request, self.template_name, {"category_form": form, "categories": document_categories_queryset()})
