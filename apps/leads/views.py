"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de CRM y leads.

EN: This module orchestrates HTTP requests, permissions, and responses for the leads domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the leads domain.
"""

from __future__ import annotations

import csv
from io import BytesIO

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from apps.accounts.views import PermissionCodeRequiredMixin
from apps.analytics.models import VehicleInteraction
from apps.analytics.services import record_vehicle_interaction
from apps.common.rate_limit import public_rate_limit_exceeded, public_rate_limited_response
from apps.branches.models import Branch
from apps.enterprise.selectors import get_primary_company
from apps.leads.forms import (
    InternalLeadForm,
    LeadActivityForm,
    LeadAssignmentForm,
    LeadSearchForm,
    LeadStatusForm,
    PublicLeadForm,
    TestDriveForm,
)
from apps.leads.models import Lead
from apps.leads.selectors import (
    filtered_lead_queryset,
    lead_detail_queryset,
    lead_metrics,
    pipeline_columns,
)
from apps.leads.services import (
    add_lead_activity,
    assign_lead,
    change_lead_status,
    convert_lead_to_customer,
    create_internal_lead,
    create_public_lead,
    create_quote_from_lead,
    schedule_test_drive,
    update_lead,
)
from apps.vehicles.selectors import public_vehicle_queryset


class PublicLeadRequestView(View):
    template_name = "leads/public/request_form.html"

    def _public_context(self):
        company = get_primary_company()
        return {
            "company": company,
            "public_settings": getattr(company, "public_settings", None) if company else None,
            "public_branches": Branch.objects.filter(is_active=True).select_related("company")[:4],
        }

    def _vehicle(self, vehicle_id):
        if not vehicle_id:
            return None
        return get_object_or_404(public_vehicle_queryset(), pk=vehicle_id)

    def get(self, request, vehicle_id=None):
        vehicle = self._vehicle(vehicle_id)
        initial = {}
        if request.GET.get("type") in dict(Lead.RequestType.choices):
            initial["request_type"] = request.GET["type"]
        form = PublicLeadForm(vehicle=vehicle, initial=initial)
        if vehicle:
            record_vehicle_interaction(
                request=request, event_type=VehicleInteraction.EventType.INFO_CLICK, vehicle=vehicle
            )
        return render(request, self.template_name, {"form": form, "vehicle": vehicle, **self._public_context()})

    def post(self, request, vehicle_id=None):
        if public_rate_limit_exceeded(request, scope="lead-request"):
            return public_rate_limited_response()
        vehicle = self._vehicle(vehicle_id)
        form = PublicLeadForm(request.POST, vehicle=vehicle)
        if form.is_valid():
            lead = create_public_lead(request=request, form=form, vehicle=vehicle)
            request.session["last_public_lead"] = str(lead.public_id)
            return redirect("leads:public_success", public_id=lead.public_id)
        return render(
            request, self.template_name,
            {"form": form, "vehicle": vehicle, **self._public_context()}, status=400,
        )


class PublicLeadSuccessView(TemplateView):
    template_name = "leads/public/request_success.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        public_id = str(kwargs["public_id"])
        if self.request.session.get("last_public_lead") == public_id:
            ctx["lead"] = (
                Lead.objects.filter(public_id=public_id)
                .select_related("vehicle", "vehicle__brand", "vehicle__model", "vehicle__model__brand")
                .first()
            )
        return ctx


class LeadAccessMixin(PermissionCodeRequiredMixin):
    permission_code = "leads.view"


class InternalLeadListView(LeadAccessMixin, ListView):
    template_name = "leads/internal/lead_list.html"
    context_object_name = "leads"
    paginate_by = 25

    def get_queryset(self):
        self.filter_form = LeadSearchForm(self.request.GET or None, user=self.request.user)
        cleaned = self.filter_form.cleaned_data if self.filter_form.is_valid() else {}
        return filtered_lead_queryset(self.request.user, cleaned)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter_form"] = self.filter_form
        ctx["now"] = timezone.now()
        ctx["metrics"] = lead_metrics(self.request.user)
        query = self.request.GET.copy()
        query.pop("page", None)
        ctx["filter_query"] = query.urlencode()
        return ctx


class InternalLeadPipelineView(LeadAccessMixin, TemplateView):
    template_name = "leads/internal/pipeline.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["columns"] = pipeline_columns(self.request.user)
        ctx["metrics"] = lead_metrics(self.request.user)
        return ctx


class InternalLeadDetailView(LeadAccessMixin, DetailView):
    template_name = "leads/internal/lead_detail.html"
    context_object_name = "lead"

    def get_queryset(self):
        return lead_detail_queryset(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["activity_form"] = LeadActivityForm()
        ctx["status_form"] = LeadStatusForm(
            initial={"status": self.object.status, "next_follow_up_at": self.object.next_follow_up_at}
        )
        ctx["assignment_form"] = LeadAssignmentForm(
            initial={"branch": self.object.branch, "assigned_advisor": self.object.assigned_advisor},
            user=self.request.user,
        )
        ctx["test_drive_form"] = TestDriveForm(lead=self.object, user=self.request.user)
        return ctx


class InternalLeadCreateView(PermissionCodeRequiredMixin, CreateView):
    permission_code = "leads.manage"
    model = Lead
    form_class = InternalLeadForm
    template_name = "leads/internal/lead_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        vehicle_id = self.request.GET.get("vehicle")
        if vehicle_id:
            initial["vehicle"] = vehicle_id
        return initial

    def form_valid(self, form):
        self.object = create_internal_lead(actor=self.request.user, form=form)
        messages.success(self.request, "Lead creado correctamente.")
        return redirect("leads_internal:detail", pk=self.object.pk)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["mode"] = "create"
        ctx["page_heading"] = "Crear lead"
        return ctx


class InternalLeadUpdateView(PermissionCodeRequiredMixin, DetailView):
    permission_code = "leads.manage"
    template_name = "leads/internal/lead_form.html"
    context_object_name = "lead"

    def get_queryset(self):
        return lead_detail_queryset(self.request.user)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        return self.render_to_response(
            self.get_context_data(
                form=InternalLeadForm(instance=self.object, user=request.user),
                mode="update",
                page_heading="Editar lead",
            )
        )

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = InternalLeadForm(request.POST, instance=self.object, user=request.user)
        if form.is_valid():
            self.object = update_lead(actor=request.user, lead=self.object, form=form)
            messages.success(request, "Lead actualizado correctamente.")
            return redirect("leads_internal:detail", pk=self.object.pk)
        return self.render_to_response(self.get_context_data(form=form, mode="update", page_heading="Editar lead"))


class InternalLeadStatusView(PermissionCodeRequiredMixin, View):
    permission_code = "leads.manage"

    def post(self, request, pk):
        lead = get_object_or_404(lead_detail_queryset(request.user), pk=pk)
        form = LeadStatusForm(request.POST)
        if form.is_valid():
            change_lead_status(actor=request.user, lead=lead, **form.cleaned_data)
            messages.success(request, "Estado actualizado correctamente.")
        else:
            messages.error(request, "No se pudo cambiar el estado. Revisa los datos.")
        return redirect("leads_internal:detail", pk=lead.pk)


class InternalLeadActivityView(PermissionCodeRequiredMixin, View):
    permission_code = "leads.manage"

    def post(self, request, pk):
        lead = get_object_or_404(lead_detail_queryset(request.user), pk=pk)
        form = LeadActivityForm(request.POST)
        if form.is_valid():
            add_lead_activity(actor=request.user, lead=lead, form=form)
            messages.success(request, "Actividad registrada.")
        else:
            messages.error(request, "No se pudo registrar la actividad.")
        return redirect("leads_internal:detail", pk=lead.pk)


class InternalLeadAssignmentView(PermissionCodeRequiredMixin, View):
    permission_code = "leads.assign"

    def post(self, request, pk):
        lead = get_object_or_404(lead_detail_queryset(request.user), pk=pk)
        form = LeadAssignmentForm(request.POST, user=request.user)
        if form.is_valid():
            assign_lead(
                actor=request.user,
                lead=lead,
                branch=form.cleaned_data["branch"],
                advisor=form.cleaned_data["assigned_advisor"],
                note=form.cleaned_data["note"],
            )
            messages.success(request, "Asignación actualizada.")
        else:
            messages.error(request, "No se pudo actualizar la asignación.")
        return redirect("leads_internal:detail", pk=lead.pk)


class InternalLeadTestDriveView(PermissionCodeRequiredMixin, View):
    permission_code = "leads.manage"

    def post(self, request, pk):
        lead = get_object_or_404(lead_detail_queryset(request.user), pk=pk)
        form = TestDriveForm(request.POST, lead=lead, user=request.user)
        if form.is_valid():
            schedule_test_drive(actor=request.user, lead=lead, form=form)
            messages.success(request, "Test drive agendado.")
        else:
            messages.error(request, "No se pudo agendar el test drive. Revisa fechas, vehículo y sucursal.")
        return redirect("leads_internal:detail", pk=lead.pk)


class InternalLeadConvertCustomerView(PermissionCodeRequiredMixin, View):
    permission_code = "leads.manage"

    def post(self, request, pk):
        lead = get_object_or_404(lead_detail_queryset(request.user), pk=pk)
        try:
            customer = convert_lead_to_customer(actor=request.user, lead=lead)
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
            return redirect("leads_internal:detail", pk=lead.pk)
        messages.success(request, f"Cliente relacionado: {customer.display_name}.")
        return redirect("customers_internal:detail", pk=customer.pk)


class InternalLeadCreateQuoteView(PermissionCodeRequiredMixin, View):
    permission_code = "sales.quote"

    def post(self, request, pk):
        lead = get_object_or_404(lead_detail_queryset(request.user, permission_codes=("sales.quote",)), pk=pk)
        try:
            sale = create_quote_from_lead(actor=request.user, lead=lead)
            messages.success(request, f"Cotización {sale.number} creada desde el lead.")
            return redirect("sales_internal:detail", pk=sale.pk)
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
            return redirect("leads_internal:detail", pk=lead.pk)


class InternalLeadExportView(LeadAccessMixin, View):
    """ES: Agrupa el componente «internal lead export view» del dominio de CRM y leads y sus reglas relacionadas. Además, aplica autorización en backend, rechaza estados o entradas inválidas.

    EN: Groups the «internal lead export view» component and its related rules in the leads domain. It also enforces server-side authorization, rejects invalid input or state.
    """

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.has_perm_code("leads.export"):
            raise PermissionDenied("No tienes permiso para exportar leads.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        """ES: Procesa solicitudes GET de InternalLeadExportView aplicando el flujo del dominio de CRM y leads. Además, rechaza estados o entradas inválidas.

        EN: Processes GET requests on InternalLeadExportView using the leads domain flow. It also rejects invalid input or state.
        """

        form = LeadSearchForm(request.GET or None, user=request.user)
        qs = filtered_lead_queryset(request.user, form.cleaned_data if form.is_valid() else {})[:20000]
        headers = [
            "Código",
            "Fecha",
            "Nombre",
            "Correo",
            "Teléfono",
            "WhatsApp",
            "Ciudad",
            "Provincia",
            "Solicitud",
            "Estado",
            "Prioridad",
            "Origen",
            "Sucursal",
            "Asesor",
            "Vehículo",
            "Puntaje",
            "Seguimiento",
            "Cliente",
            "Cotización/Venta",
        ]
        rows = [
            [
                lead.code,
                lead.created_at.isoformat(),
                lead.full_name,
                lead.email,
                lead.phone,
                lead.whatsapp,
                lead.city,
                lead.province,
                lead.get_request_type_display(),
                lead.get_status_display(),
                lead.get_priority_display(),
                lead.get_source_display(),
                lead.branch.name if lead.branch else "",
                lead.assigned_advisor.get_full_name() or lead.assigned_advisor.username
                if lead.assigned_advisor
                else "",
                lead.vehicle.internal_code if lead.vehicle else lead.vehicle_interest_label,
                lead.score,
                lead.next_follow_up_at.isoformat() if lead.next_follow_up_at else "",
                lead.customer.display_name if lead.customer else "",
                lead.linked_sale.number if lead.linked_sale else "",
            ]
            for lead in qs
        ]
        export_format = request.GET.get("format", "csv")
        if export_format == "xlsx":
            wb = Workbook()
            ws = wb.active
            ws.title = "leads"
            ws.append(headers)
            for cell in ws[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="1F4E78")
            for row in rows:
                ws.append(row)
            ws.freeze_panes = "A2"
            ws.auto_filter.ref = ws.dimensions
            for column in ws.columns:
                ws.column_dimensions[column[0].column_letter].width = min(
                    max(len(str(c.value or "")) for c in column) + 2, 42
                )
            output = BytesIO()
            wb.save(output)
            response = HttpResponse(
                output.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            filename = "vinova_pro_leads.xlsx"
        else:
            response = HttpResponse(content_type="text/csv; charset=utf-8")
            response.write("\ufeff")
            writer = csv.writer(response)
            writer.writerow(headers)
            writer.writerows(rows)
            filename = "vinova_pro_leads.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response
