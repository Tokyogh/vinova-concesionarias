"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de reportes.

EN: This module orchestrates HTTP requests, permissions, and responses for the reports domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the reports domain.
"""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import TemplateView

from apps.reports.forms import ReportFilterForm
from apps.reports import selectors
from apps.reports.services import export_csv_response, export_xlsx_response, get_report_context, report_title, rows_for_report


class ReportAccessMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.is_superuser or request.user.can_view_reports):
            raise PermissionDenied("No tienes permiso para ver reportes.")
        return super().dispatch(request, *args, **kwargs)

    def build_form(self):
        form = ReportFilterForm(self.request.GET or None, user=self.request.user)
        form.is_valid()
        return form

    def build_filters(self, form):
        return selectors.filters_from_form(form)


class ReportsHomeView(ReportAccessMixin, TemplateView):
    template_name = "reports/internal/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        form = self.build_form()
        filters = self.build_filters(form)
        ctx.update(selectors.reports_home_context(filters, self.request.user))
        ctx.update({"filter_form": form, "filters": filters, "report_type": "executive", "report_title": "Reportes empresariales"})
        return ctx


class ReportDetailView(ReportAccessMixin, TemplateView):
    template_name = "reports/internal/detail.html"
    report_type = "sales"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        form = self.build_form()
        filters = self.build_filters(form)
        ctx.update(get_report_context(self.report_type, filters, self.request.user))
        ctx.update(
            {
                "filter_form": form,
                "filters": filters,
                "report_type": self.report_type,
                "report_title": report_title(self.report_type),
                "can_export_reports": self.request.user.is_superuser or self.request.user.has_perm_code("data.export"),
            }
        )
        return ctx


class ReportExportView(ReportAccessMixin, View):
    allowed_formats = {"csv", "xlsx"}

    def get(self, request, report_type, export_format):
        if not (request.user.is_superuser or request.user.has_perm_code("data.export")):
            raise PermissionDenied("No tienes permiso para exportar reportes.")
        if export_format not in self.allowed_formats or report_type not in DynamicReportDetailView.allowed_reports:
            return redirect(reverse("reports_internal:detail", kwargs={"report_type": report_type}))
        form = self.build_form()
        filters = self.build_filters(form)
        if export_format == "xlsx":
            return export_xlsx_response(report_type, filters, request.user)
        return export_csv_response(report_type, filters, request.user)


class ReportPrintView(ReportAccessMixin, TemplateView):
    template_name = "reports/internal/print.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        report_type = self.kwargs.get("report_type", "executive")
        form = self.build_form()
        filters = self.build_filters(form)
        title, headers, rows = rows_for_report(report_type, filters, self.request.user)
        ctx.update({"report_type": report_type, "report_title": title, "headers": headers, "rows": rows, "filters": filters})
        return ctx


class DynamicReportDetailView(ReportDetailView):
    allowed_reports = {"sales", "branches", "vehicles", "inventory", "stock_movements", "invoices", "customers", "activity", "products"}

    def dispatch(self, request, *args, **kwargs):
        self.report_type = kwargs.get("report_type", "sales")
        if self.report_type not in self.allowed_reports:
            return redirect(reverse("reports_internal:home"))
        return super().dispatch(request, *args, **kwargs)
