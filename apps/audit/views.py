"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de auditoría.

EN: This module orchestrates HTTP requests, permissions, and responses for the audit domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the audit domain.
"""

from __future__ import annotations

import csv
from io import BytesIO

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from apps.accounts.views import PermissionCodeRequiredMixin
from apps.audit.forms import AuditFilterForm, SecurityAlertFilterForm, SecurityAlertResolutionForm
from apps.audit.selectors import (
    audit_dashboard_metrics,
    filtered_alert_queryset,
    filtered_audit_queryset,
    scoped_alert_queryset,
    scoped_audit_queryset,
)
from apps.audit.services import audit_log, verify_audit_chain


class AuditAccessMixin(PermissionCodeRequiredMixin):
    permission_code = "audit.view"


class AuditLogListView(AuditAccessMixin, ListView):
    template_name = "audit/internal/audit_list.html"
    context_object_name = "logs"
    paginate_by = 30

    def get_queryset(self):
        self.filter_form = AuditFilterForm(self.request.GET or None, user=self.request.user)
        cleaned = self.filter_form.cleaned_data if self.filter_form.is_valid() else {}
        return filtered_audit_queryset(self.request.user, cleaned)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter_form"] = self.filter_form
        ctx["metrics"] = audit_dashboard_metrics(self.request.user)
        query = self.request.GET.copy()
        query.pop("page", None)
        ctx["filter_query"] = query.urlencode()
        return ctx


class AuditLogDetailView(AuditAccessMixin, DetailView):
    template_name = "audit/internal/audit_detail.html"
    context_object_name = "log"
    slug_field = "event_id"
    slug_url_kwarg = "event_id"

    def get_queryset(self):
        return scoped_audit_queryset(self.request.user)


class AuditExportView(AuditAccessMixin, View):
    """ES: Agrupa el componente «audit export view» del dominio de auditoría y sus reglas relacionadas. Además, aplica autorización en backend, registra efectos auditables, rechaza estados o entradas inválidas.

    EN: Groups the «audit export view» component and its related rules in the audit domain. It also enforces server-side authorization, records auditable effects, rejects invalid input or state.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.has_perm_code("audit.export"):
            raise PermissionDenied("No tienes permiso para exportar auditoría.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        """ES: Procesa solicitudes GET de AuditExportView aplicando el flujo del dominio de auditoría. Además, registra efectos auditables, rechaza estados o entradas inválidas.

        EN: Processes GET requests on AuditExportView using the audit domain flow. It also records auditable effects, rejects invalid input or state.
        """

        form = AuditFilterForm(request.GET or None, user=request.user, permission_code="audit.export")
        qs = filtered_audit_queryset(request.user, form.cleaned_data if form.is_valid() else {}, permission_code="audit.export")[:10000]
        export_format = request.GET.get("format", "csv").lower()
        headers = ["Fecha", "Evento", "Usuario", "Roles", "Sucursal", "Acción", "Categoría", "Severidad", "Resultado", "Objeto", "ID objeto", "IP", "Método", "Ruta", "Request ID", "Hash"]
        rows = [
            [
                log.occurred_at.isoformat(), str(log.event_id), log.user_display_snapshot or log.username_snapshot,
                ", ".join(role.get("role__name", role.get("role__code", "")) for role in log.role_snapshot),
                log.branch.name if log.branch else "", log.action, log.get_category_display(), log.get_severity_display(),
                log.get_result_display(), log.object_repr, log.object_id, str(log.ip_address or ""), log.http_method,
                log.request_path, str(log.request_id or ""), log.entry_hash or "",
            ]
            for log in qs
        ]
        if export_format == "xlsx":
            workbook = Workbook()
            sheet = workbook.active
            sheet.title = "auditoria"
            sheet.append(headers)
            for cell in sheet[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="1F4E78")
            for row in rows:
                sheet.append(row)
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
            for column in sheet.columns:
                letter = column[0].column_letter
                sheet.column_dimensions[letter].width = min(max(len(str(cell.value or "")) for cell in column) + 2, 45)
            output = BytesIO()
            workbook.save(output)
            response = HttpResponse(output.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
            filename = "vinova_pro_auditoria.xlsx"
        else:
            response = HttpResponse(content_type="text/csv; charset=utf-8")
            response.write("\ufeff")
            writer = csv.writer(response)
            writer.writerow(headers)
            writer.writerows(rows)
            filename = "vinova_pro_auditoria.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        audit_log(user=request.user, action="audit.export", after={"format": export_format, "rows": len(rows)})
        return response


class AuditIntegrityView(AuditAccessMixin, TemplateView):
    template_name = "audit/internal/integrity.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["integrity"] = verify_audit_chain(queryset=scoped_audit_queryset(self.request.user), strict_links=self.request.user.is_superuser)
        return ctx


class SecurityAlertListView(AuditAccessMixin, ListView):
    template_name = "audit/internal/alert_list.html"
    context_object_name = "alerts"
    paginate_by = 25

    def get_queryset(self):
        self.filter_form = SecurityAlertFilterForm(self.request.GET or None, user=self.request.user)
        cleaned = self.filter_form.cleaned_data if self.filter_form.is_valid() else {}
        return filtered_alert_queryset(self.request.user, cleaned)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter_form"] = self.filter_form
        return ctx


class SecurityAlertDetailView(AuditAccessMixin, DetailView):
    template_name = "audit/internal/alert_detail.html"
    context_object_name = "alert"
    slug_field = "alert_id"
    slug_url_kwarg = "alert_id"

    def get_queryset(self):
        return scoped_alert_queryset(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["resolution_form"] = SecurityAlertResolutionForm(initial={"status": self.object.status, "resolution_notes": self.object.resolution_notes})
        return ctx


class SecurityAlertUpdateView(AuditAccessMixin, View):
    def post(self, request, alert_id):
        if not request.user.has_perm_code("audit.manage_alerts"):
            raise PermissionDenied("No tienes permiso para gestionar alertas.")
        alert = get_object_or_404(scoped_alert_queryset(request.user, permission_code="audit.manage_alerts"), alert_id=alert_id)
        form = SecurityAlertResolutionForm(request.POST)
        if form.is_valid():
            before = {"status": alert.status, "resolution_notes": alert.resolution_notes}
            alert.resolve(actor=request.user, status=form.cleaned_data["status"], notes=form.cleaned_data["resolution_notes"])
            audit_log(
                user=request.user,
                action="audit.alert.update",
                target=alert,
                before=before,
                after={"status": alert.status, "resolution_notes": alert.resolution_notes},
            )
            messages.success(request, "Alerta actualizada correctamente.")
        else:
            messages.error(request, "No se pudo actualizar la alerta.")
        return redirect(reverse("audit_internal:alert_detail", kwargs={"alert_id": alert.alert_id}))
