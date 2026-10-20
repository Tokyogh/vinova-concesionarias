"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de analítica.

EN: This module orchestrates HTTP requests, permissions, and responses for the analytics domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the analytics domain.
"""

from __future__ import annotations

from io import BytesIO

from django.core.exceptions import PermissionDenied
from django.db.models import Sum
from django.http import HttpResponse
from django.views import View
from django.views.generic import DetailView, TemplateView
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill

from apps.accounts.models import User
from apps.accounts.scopes import accessible_users_queryset, scope_queryset_to_user_branches
from apps.accounts.views import PermissionCodeRequiredMixin
from apps.analytics.forms import CommercialAnalyticsFilterForm
from apps.analytics.selectors import commercial_dashboard_data, filtered_commercial_leads
from apps.audit.services import audit_log
from apps.customers.selectors import customer_detail_queryset
from apps.leads.models import Lead
from apps.leads.selectors import scoped_lead_queryset
from apps.sales.models import SaleRecord


class AnalyticsAccessMixin(PermissionCodeRequiredMixin):
    permission_code = "analytics.view"


class CommercialAnalyticsView(AnalyticsAccessMixin, TemplateView):
    template_name = "analytics/internal/commercial_dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        form = CommercialAnalyticsFilterForm(self.request.GET or None, user=self.request.user)
        cleaned = form.cleaned_data if form.is_valid() else {}
        ctx["filter_form"] = form
        ctx.update(commercial_dashboard_data(self.request.user, cleaned))
        ctx["filter_query"] = self.request.GET.urlencode()
        return ctx


class CommercialAnalyticsExportView(AnalyticsAccessMixin, View):
    """Export commercial analytics after enforcing module and permission gates."""

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.has_perm_code("analytics.export"):
            raise PermissionDenied("No tienes permiso para exportar analítica comercial.")
        return super().dispatch(request, *args, **kwargs)

    def get(self, request):
        """ES: Procesa solicitudes GET de CommercialAnalyticsExportView aplicando el flujo del dominio de analítica. Además, registra efectos auditables, rechaza estados o entradas inválidas.

        EN: Processes GET requests on CommercialAnalyticsExportView using the analytics domain flow. It also records auditable effects, rejects invalid input or state.
        """

        form = CommercialAnalyticsFilterForm(
            request.GET,
            user=request.user,
            permission_codes=("analytics.export",),
        )
        if not form.is_valid():
            return HttpResponse("Filtros inválidos.", status=400, content_type="text/plain; charset=utf-8")
        cleaned = form.cleaned_data
        leads = filtered_commercial_leads(request.user, cleaned, permission_codes=("analytics.export",))[:10000]
        data = commercial_dashboard_data(request.user, cleaned, permission_codes=("analytics.export",))
        wb = Workbook()
        ws = wb.active
        ws.title = "leads_dataset"
        headers = [
            "lead_code",
            "created_at",
            "status",
            "priority",
            "source",
            "request_type",
            "city",
            "province",
            "branch",
            "advisor",
            "vehicle_code",
            "brand",
            "model",
            "year",
            "score",
            "customer_id",
            "sale_number",
            "won",
        ]
        ws.append(headers)
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill("solid", fgColor="1F4E78")
        for lead in leads:
            ws.append(
                [
                    lead.code,
                    lead.created_at.isoformat(),
                    lead.status,
                    lead.priority,
                    lead.source,
                    lead.request_type,
                    lead.city,
                    lead.province,
                    lead.branch.name if lead.branch else "",
                    lead.assigned_advisor.username if lead.assigned_advisor else "",
                    lead.vehicle.internal_code if lead.vehicle else "",
                    lead.vehicle.brand.name if lead.vehicle else lead.interested_brand,
                    lead.vehicle.model.name if lead.vehicle else lead.interested_model,
                    lead.vehicle.year if lead.vehicle else "",
                    lead.score,
                    lead.customer_id or "",
                    lead.linked_sale.number if lead.linked_sale else "",
                    1 if lead.status == Lead.Status.WON else 0,
                ]
            )
        ws.freeze_panes = "A2"
        ws.auto_filter.ref = ws.dimensions
        for title, rows, fields in [
            ("funnel", data["funnel"], ["code", "label", "count"]),
            (
                "vehicles",
                data["vehicles"],
                [
                    "vehicle__internal_code",
                    "vehicle__brand__name",
                    "vehicle__model__name",
                    "vehicle__year",
                    "leads",
                    "clicks",
                    "won",
                    "conversion",
                ],
            ),
            ("cities", data["cities"], ["city", "province", "leads", "won"]),
            ("sources", data["sources"], ["source", "label", "leads", "won", "conversion"]),
            ("advisors", data["advisors"], ["display", "leads", "quotes", "won", "conversion"]),
        ]:
            sheet = wb.create_sheet(title)
            sheet.append(fields)
            for cell in sheet[1]:
                cell.font = Font(bold=True, color="FFFFFF")
                cell.fill = PatternFill("solid", fgColor="1F4E78")
            for row in rows:
                sheet.append([row.get(field, "") for field in fields])
            sheet.freeze_panes = "A2"
            sheet.auto_filter.ref = sheet.dimensions
        output = BytesIO()
        wb.save(output)
        audit_log(
            user=request.user,
            action="analytics.dataset_exported",
            metadata={"rows": len(leads), "format": "xlsx"},
        )
        response = HttpResponse(
            output.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
        response["Content-Disposition"] = 'attachment; filename="vinova_pro_commercial_bi.xlsx"'
        return response


class CustomerExecutiveProfileView(AnalyticsAccessMixin, DetailView):
    template_name = "analytics/internal/customer_profile.html"
    context_object_name = "customer"

    def get_queryset(self):
        return customer_detail_queryset(user=self.request.user, permission_codes=("analytics.view",))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        customer = self.object
        leads = scoped_lead_queryset(
            self.request.user, permission_codes=("analytics.view",)
        ).filter(customer=customer)
        sales = scope_queryset_to_user_branches(
            customer.sales.filter(is_deleted=False),
            user=self.request.user,
            permission_codes=("analytics.view",),
        ).select_related("branch", "advisor", "vehicle", "vehicle__brand", "vehicle__model", "vehicle__model__brand")
        ctx.update(
            {
                "leads": leads[:20],
                "sales": sales[:20],
                "interests": customer.vehicle_interests.select_related("vehicle")[:20],
                "notes": customer.notes.select_related("created_by")[:20],
                "metrics": {
                    "leads": leads.count(),
                    "active_leads": leads.exclude(status__in=[Lead.Status.WON, Lead.Status.LOST]).count(),
                    "quotes": sales.filter(kind=SaleRecord.Kind.QUOTE).count(),
                    "sales": sales.filter(status=SaleRecord.Status.SOLD).count(),
                    "purchased_total": sales.filter(status=SaleRecord.Status.SOLD).aggregate(total=Sum("total"))[
                        "total"
                    ]
                    or 0,
                },
            }
        )
        return ctx


class UserCommercialProfileView(AnalyticsAccessMixin, DetailView):
    template_name = "analytics/internal/user_profile.html"
    context_object_name = "advisor"
    model = User

    def get_queryset(self):
        return accessible_users_queryset(
            self.request.user, permission_codes=("analytics.view",)
        ).select_related("branch")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        advisor = self.object
        leads = scoped_lead_queryset(
            self.request.user, permission_codes=("analytics.view",)
        ).filter(assigned_advisor=advisor)
        sales = scope_queryset_to_user_branches(
            SaleRecord.objects.filter(advisor=advisor, is_deleted=False),
            user=self.request.user,
            permission_codes=("analytics.view",),
        ).select_related("customer", "branch", "vehicle", "vehicle__brand", "vehicle__model", "vehicle__model__brand")
        total = leads.count()
        won = leads.filter(status=Lead.Status.WON).count()
        ctx.update(
            {
                "leads": leads[:20],
                "sales": sales[:20],
                "pipeline": [
                    {"code": code, "label": label, "count": leads.filter(status=code).count()}
                    for code, label in Lead.Status.choices
                ],
                "metrics": {
                    "leads": total,
                    "open": leads.exclude(status__in=[Lead.Status.WON, Lead.Status.LOST]).count(),
                    "won": won,
                    "conversion": round(won / total * 100, 1) if total else 0,
                    "quotes": sales.filter(kind=SaleRecord.Kind.QUOTE).count(),
                    "sales": sales.filter(status=SaleRecord.Status.SOLD).count(),
                    "sales_total": sales.filter(status=SaleRecord.Status.SOLD).aggregate(total=Sum("total"))["total"]
                    or 0,
                },
            }
        )
        return ctx
