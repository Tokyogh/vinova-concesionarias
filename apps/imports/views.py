"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de importaciones.

EN: This module orchestrates HTTP requests, permissions, and responses for the imports domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the imports domain.
"""

from __future__ import annotations

import csv
import io

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, FormView, TemplateView

from apps.imports.forms import ImportBatchCreateForm, ImportFilterForm
from apps.imports.models import ImportBatch
from apps.imports.selectors import filter_import_batches, import_batch_queryset, imports_dashboard_context
from apps.imports.services import build_template_workbook, confirm_import_batch, create_import_batch, sample_template_rows, validate_import_batch


class ImportPermissionMixin:
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            from django.contrib.auth.views import redirect_to_login
            return redirect_to_login(request.get_full_path())
        if not (request.user.is_superuser or request.user.can_manage_imports):
            raise PermissionDenied("No tienes permiso para gestionar importaciones masivas.")
        return super().dispatch(request, *args, **kwargs)

    def get_import_nav(self):
        return [
            ("Resumen", reverse("imports_internal:home")),
            ("Nueva importación", reverse("imports_internal:create")),
            ("Vehículos", f"{reverse('imports_internal:create')}?type=vehicles"),
            ("Clientes", f"{reverse('imports_internal:create')}?type=customers"),
            ("Inventario", f"{reverse('imports_internal:create')}?type=inventory"),
            ("Stock", f"{reverse('imports_internal:create')}?type=stock"),
        ]

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["imports_nav"] = self.get_import_nav()
        ctx["import_types"] = ImportBatch.ImportType.choices
        return ctx


class ImportHomeView(ImportPermissionMixin, TemplateView):
    template_name = "imports/internal/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        form = ImportFilterForm(self.request.GET or None)
        qs = filter_import_batches(form, user=self.request.user)
        paginator = Paginator(qs, 15)
        page = paginator.get_page(self.request.GET.get("page"))
        ctx.update(imports_dashboard_context(user=self.request.user))
        ctx.update({"filter_form": form, "page_obj": page, "batches": page.object_list})
        return ctx


class ImportCreateView(ImportPermissionMixin, FormView):
    template_name = "imports/internal/import_form.html"
    form_class = ImportBatchCreateForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        type_from_query = self.request.GET.get("type")
        if type_from_query in dict(ImportBatch.ImportType.choices):
            initial["import_type"] = type_from_query
        return initial

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        selected_type = self.request.GET.get("type") or getattr(ctx.get("form"), "data", {}).get("import_type")
        if selected_type not in dict(ImportBatch.ImportType.choices):
            selected_type = ImportBatch.ImportType.VEHICLES
        ctx["selected_import_type"] = selected_type
        ctx["vehicle_import_mode"] = selected_type == ImportBatch.ImportType.VEHICLES
        return ctx

    def form_valid(self, form):
        try:
            batch = create_import_batch(
                actor=self.request.user,
                import_type=form.cleaned_data["import_type"],
                uploaded_file=form.cleaned_data["original_file"],
                default_branch=form.cleaned_data.get("default_branch"),
                require_vehicle_branch=form.cleaned_data.get("require_vehicle_branch", False),
                notes=form.cleaned_data.get("notes", ""),
            )
        except ValidationError as exc:
            form.add_error("original_file", exc)
            return self.form_invalid(form)
        if batch.invalid_rows:
            messages.warning(self.request, "El archivo fue recibido, pero tiene errores. Revisa el detalle por fila antes de volver a subirlo.")
        else:
            messages.success(self.request, "Archivo validado correctamente. Revisa la vista previa y confirma la importación.")
        return redirect("imports_internal:detail", pk=batch.pk)


class ImportDetailView(ImportPermissionMixin, DetailView):
    model = ImportBatch
    template_name = "imports/internal/import_detail.html"
    context_object_name = "batch"

    def get_queryset(self):
        return import_batch_queryset(user=self.request.user).prefetch_related("rows")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        rows = self.object.rows.all()[:80]
        ctx["rows"] = rows
        ctx["valid_rows_count"] = self.object.rows.filter(status="valid").count()
        return ctx


class ImportRevalidateView(ImportPermissionMixin, View):
    def post(self, request, pk):
        batch = get_object_or_404(import_batch_queryset(user=request.user), pk=pk)
        validate_import_batch(batch=batch, actor=request.user)
        if batch.invalid_rows:
            messages.warning(request, "Validación terminada con errores por fila.")
        else:
            messages.success(request, "Validación correcta. El lote puede confirmarse.")
        return redirect("imports_internal:detail", pk=batch.pk)


class ImportConfirmView(ImportPermissionMixin, View):
    def post(self, request, pk):
        batch = get_object_or_404(import_batch_queryset(user=request.user), pk=pk)
        try:
            confirm_import_batch(batch=batch, actor=request.user)
            if batch.status == ImportBatch.Status.COMPLETED:
                messages.success(request, "Importación confirmada y aplicada correctamente.")
            else:
                messages.error(request, "La importación terminó con errores. Revisa el detalle del lote.")
        except ValidationError as exc:
            messages.error(request, exc.message if hasattr(exc, "message") else str(exc))
        return redirect("imports_internal:detail", pk=batch.pk)


class ImportTemplateDownloadView(ImportPermissionMixin, View):
    def get(self, request, import_type):
        if import_type not in dict(ImportBatch.ImportType.choices):
            import_type = ImportBatch.ImportType.VEHICLES
        fmt = request.GET.get("format", "csv").lower()
        if fmt == "xlsx":
            workbook = build_template_workbook(import_type)
            output = io.BytesIO()
            workbook.save(output)
            output.seek(0)
            response = HttpResponse(output.read(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            response["Content-Disposition"] = f'attachment; filename="plantilla_{import_type}_vinova.xlsx"'
            return response
        headers, _example_rows = sample_template_rows(import_type)
        response = HttpResponse(content_type="text/csv; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="plantilla_{import_type}_vinova.csv"'
        response.write("\ufeff")
        writer = csv.writer(response)
        writer.writerow(headers)
        return response
