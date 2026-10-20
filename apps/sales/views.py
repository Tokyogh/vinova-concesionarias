"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de ventas.

EN: This module orchestrates HTTP requests, permissions, and responses for the sales domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the sales domain.
"""

from __future__ import annotations

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from apps.accounts.views import PermissionCodeRequiredMixin
from apps.sales.forms import SaleActionForm, SaleLineForm, SalePaymentForm, SaleRecordForm, SaleSearchForm
from apps.sales.models import SaleRecord
from apps.sales.selectors import (
    sale_detail_queryset,
    sale_lines_queryset,
    sale_list_queryset,
    sale_payments_queryset,
    sale_status_history_queryset,
    sales_metrics,
    sales_needing_attention_queryset,
)
from apps.sales.services import (
    add_sale_line,
    add_sale_payment,
    cancel_sale,
    confirm_sale,
    create_sale,
    expire_sale,
    reserve_sale,
    update_sale,
    void_sale_payment,
)


class SalesPermissionFallbackMixin(PermissionCodeRequiredMixin):
    permission_code = "sales.quote"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.has_perm_code("sales.quote"):
            if request.user.has_perm_code("sales.reserve"):
                self.permission_code = "sales.reserve"
            elif request.user.has_perm_code("sales.sell"):
                self.permission_code = "sales.sell"
        return super().dispatch(request, *args, **kwargs)


class InternalSaleListView(SalesPermissionFallbackMixin, ListView):
    template_name = "sales/internal/sale_list.html"
    context_object_name = "sales"
    paginate_by = 20

    def get_queryset(self):
        self.search_form = SaleSearchForm(self.request.GET, user=self.request.user)
        query = status = kind = sort = ""
        branch = None
        if self.search_form.is_valid():
            query = self.search_form.cleaned_data.get("q", "")
            status = self.search_form.cleaned_data.get("status", "")
            kind = self.search_form.cleaned_data.get("kind", "")
            branch = self.search_form.cleaned_data.get("branch")
            sort = self.search_form.cleaned_data.get("sort", "")
        return sale_list_queryset(self.request.user, query=query, status=status, kind=kind, branch=branch, sort=sort)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_form"] = self.search_form
        ctx["metrics"] = sales_metrics(self.request.user)
        ctx["attention_sales"] = sales_needing_attention_queryset(self.request.user)[:8]
        return ctx


class InternalSaleCreateView(PermissionCodeRequiredMixin, CreateView):
    permission_code = "sales.quote"
    model = SaleRecord
    form_class = SaleRecordForm
    template_name = "sales/internal/sale_form.html"

    def form_valid(self, form):
        try:
            self.object = create_sale(actor=self.request.user, form=form)
        except ValidationError as exc:
            form.add_error(None, exc.message if hasattr(exc, "message") else exc)
            return self.form_invalid(form)
        messages.success(self.request, "Operación comercial creada correctamente.")
        return redirect("sales_internal:detail", pk=self.object.pk)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["mode"] = "create"
        ctx["page_heading"] = "Crear cotización / reserva"
        return ctx


class InternalSaleDetailView(SalesPermissionFallbackMixin, DetailView):
    template_name = "sales/internal/sale_detail.html"
    context_object_name = "sale"

    def get_queryset(self):
        return sale_detail_queryset(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["lines"] = sale_lines_queryset(self.object)
        ctx["payments"] = sale_payments_queryset(self.object)
        ctx["can_void_payments"] = self.request.user.has_perm_code("sales.sell", branch=self.object.branch)
        ctx["history"] = sale_status_history_queryset(self.object)[:20]
        ctx["line_form"] = SaleLineForm()
        ctx["payment_form"] = SalePaymentForm()
        ctx["reserve_form"] = SaleActionForm(require_reservation_date=True, initial={"reserved_until": self.object.reserved_until})
        ctx["action_form"] = SaleActionForm()
        return ctx


class InternalSaleUpdateView(PermissionCodeRequiredMixin, DetailView):
    permission_code = "sales.quote"
    template_name = "sales/internal/sale_form.html"
    context_object_name = "sale"

    def get_queryset(self):
        return sale_detail_queryset(self.request.user)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = SaleRecordForm(instance=self.object)
        return self.render_to_response(self.get_context_data(form=form, mode="update", page_heading="Editar operación comercial"))

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = SaleRecordForm(request.POST, instance=self.object)
        if form.is_valid():
            try:
                self.object = update_sale(actor=request.user, sale=self.object, form=form)
            except ValidationError as exc:
                form.add_error(None, exc.message if hasattr(exc, "message") else exc)
            else:
                messages.success(request, "Operación actualizada correctamente.")
                return redirect("sales_internal:detail", pk=self.object.pk)
        return self.render_to_response(self.get_context_data(form=form, mode="update", page_heading="Editar operación comercial"))


class InternalSaleLineCreateView(PermissionCodeRequiredMixin, View):
    permission_code = "sales.quote"

    def post(self, request, pk):
        sale = get_object_or_404(sale_detail_queryset(request.user), pk=pk)
        form = SaleLineForm(request.POST)
        if form.is_valid():
            try:
                add_sale_line(actor=request.user, sale=sale, form=form)
                messages.success(request, "Línea agregada correctamente.")
            except ValidationError as exc:
                messages.error(request, exc.message if hasattr(exc, "message") else str(exc))
        else:
            messages.error(request, "No se pudo agregar la línea. Revisa los datos ingresados.")
        return redirect("sales_internal:detail", pk=sale.pk)


class InternalSalePaymentCreateView(PermissionCodeRequiredMixin, View):
    permission_code = "sales.sell"

    def post(self, request, pk):
        sale = get_object_or_404(sale_detail_queryset(request.user), pk=pk)
        form = SalePaymentForm(request.POST)
        if form.is_valid():
            try:
                add_sale_payment(actor=request.user, sale=sale, form=form)
                messages.success(request, "Pago registrado correctamente.")
            except ValidationError as exc:
                messages.error(request, exc.message if hasattr(exc, "message") else str(exc))
        else:
            messages.error(request, "No se pudo registrar el pago. Revisa los datos.")
        return redirect("sales_internal:detail", pk=sale.pk)


class InternalSalePaymentVoidView(PermissionCodeRequiredMixin, View):
    permission_code = "sales.sell"

    def post(self, request, pk, payment_pk):
        sale = get_object_or_404(sale_detail_queryset(request.user), pk=pk)
        payment = get_object_or_404(sale_payments_queryset(sale), pk=payment_pk)
        try:
            void_sale_payment(actor=request.user, payment=payment, reason=request.POST.get("reason", ""))
            messages.success(request, "Pago anulado correctamente.")
        except ValidationError as exc:
            messages.error(request, exc.message if hasattr(exc, "message") else str(exc))
        return redirect("sales_internal:detail", pk=sale.pk)


class InternalSaleActionView(View):
    """Dispatch sale lifecycle mutations to permission-aware domain services."""

    def post(self, request, pk, action):
        """ES: Procesa solicitudes POST de InternalSaleActionView aplicando el flujo del dominio de ventas. Además, aplica autorización en backend, rechaza estados o entradas inválidas.

        EN: Processes POST requests on InternalSaleActionView using the sales domain flow. It also enforces server-side authorization, rejects invalid input or state.
        """

        sale = get_object_or_404(sale_detail_queryset(request.user), pk=pk)
        if action == "reserve":
            if not request.user.has_perm_code("sales.reserve"):
                messages.error(request, "No tienes permiso para reservar operaciones.")
                return redirect("sales_internal:detail", pk=sale.pk)
            form = SaleActionForm(request.POST, require_reservation_date=True)
            if form.is_valid():
                try:
                    reserve_sale(actor=request.user, sale=sale, reserved_until=form.cleaned_data.get("reserved_until"), note=form.cleaned_data.get("note", ""))
                    messages.success(request, "Reserva registrada correctamente.")
                except ValidationError as exc:
                    messages.error(request, exc.message if hasattr(exc, "message") else str(exc))
            else:
                messages.error(request, "No se pudo reservar. Revisa la fecha y observación.")
        elif action == "confirm":
            if not request.user.has_perm_code("sales.sell"):
                messages.error(request, "No tienes permiso para confirmar ventas.")
                return redirect("sales_internal:detail", pk=sale.pk)
            form = SaleActionForm(request.POST)
            if form.is_valid():
                try:
                    confirm_sale(actor=request.user, sale=sale, note=form.cleaned_data.get("note", ""))
                    messages.success(request, "Venta confirmada correctamente.")
                except ValidationError as exc:
                    messages.error(request, exc.message if hasattr(exc, "message") else str(exc))
        elif action == "cancel":
            if not request.user.has_perm_code("sales.quote") and not request.user.has_perm_code("sales.reserve"):
                messages.error(request, "No tienes permiso para cancelar operaciones.")
                return redirect("sales_internal:detail", pk=sale.pk)
            form = SaleActionForm(request.POST)
            if form.is_valid():
                try:
                    cancel_sale(actor=request.user, sale=sale, note=form.cleaned_data.get("note", ""))
                    messages.success(request, "Operación cancelada correctamente.")
                except ValidationError as exc:
                    messages.error(request, exc.message if hasattr(exc, "message") else str(exc))
        elif action == "expire":
            if not request.user.has_perm_code("sales.reserve"):
                messages.error(request, "No tienes permiso para expirar reservas/cotizaciones.")
                return redirect("sales_internal:detail", pk=sale.pk)
            try:
                expire_sale(actor=request.user, sale=sale, note="Marcado manualmente como expirado")
                messages.success(request, "Operación marcada como expirada.")
            except ValidationError as exc:
                messages.error(request, exc.message if hasattr(exc, "message") else str(exc))
        else:
            messages.error(request, "Acción no válida.")
        return redirect("sales_internal:detail", pk=sale.pk)


class InternalSalesAttentionView(SalesPermissionFallbackMixin, ListView):
    template_name = "sales/internal/attention.html"
    context_object_name = "sales"
    paginate_by = 30

    def get_queryset(self):
        return sales_needing_attention_queryset(self.request.user)
