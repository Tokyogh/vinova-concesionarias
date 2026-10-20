"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de facturación.

EN: This module orchestrates HTTP requests, permissions, and responses for the invoices domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the invoices domain.
"""

from __future__ import annotations

from pathlib import Path

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView

from apps.accounts.views import PermissionCodeRequiredMixin
from apps.documents.downloads import open_private_file_or_404
from apps.documents.services import register_document_download
from apps.invoices.forms import InvoiceActionForm, InvoiceFromSaleForm, InvoiceLineForm, InvoicePaymentApplicationForm, InvoiceSearchForm
from apps.invoices.selectors import invoice_detail_queryset, invoice_list_queryset, invoice_metrics, invoice_payments_queryset, ready_sales_for_invoicing_queryset
from apps.invoices.services import add_invoice_line, apply_confirmed_sale_payments, apply_payment, create_invoice_from_sale, ensure_invoice_pdf, issue_invoice, void_invoice


class InvoiceAccessMixin(PermissionCodeRequiredMixin):
    permission_code = "invoices.view"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.has_perm_code("invoices.view"):
            if request.user.has_perm_code("invoices.issue"):
                self.permission_code = "invoices.issue"
            elif request.user.has_perm_code("invoices.manage"):
                self.permission_code = "invoices.manage"
        return super().dispatch(request, *args, **kwargs)


class InvoiceIssueRequiredMixin(PermissionCodeRequiredMixin):
    permission_code = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not (request.user.has_perm_code("invoices.issue") or request.user.has_perm_code("invoices.manage")):
            raise PermissionDenied("No tienes permiso para emitir comprobantes.")
        return super().dispatch(request, *args, **kwargs)


class InvoiceListView(InvoiceAccessMixin, ListView):
    template_name = "invoices/internal/invoice_list.html"
    context_object_name = "invoices"
    paginate_by = 20

    def get_queryset(self):
        self.search_form = InvoiceSearchForm(self.request.GET, user=self.request.user)
        query = status = invoice_type = sort = ""
        branch = None
        if self.search_form.is_valid():
            query = self.search_form.cleaned_data.get("q", "")
            status = self.search_form.cleaned_data.get("status", "")
            invoice_type = self.search_form.cleaned_data.get("invoice_type", "")
            branch = self.search_form.cleaned_data.get("branch")
            sort = self.search_form.cleaned_data.get("sort", "")
        return invoice_list_queryset(self.request.user, query=query, status=status, invoice_type=invoice_type, branch=branch, sort=sort)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_form"] = self.search_form
        ctx["metrics"] = invoice_metrics(self.request.user)
        ctx["ready_sales"] = ready_sales_for_invoicing_queryset(self.request.user)[:8]
        return ctx


class InvoiceCreateFromSaleView(InvoiceIssueRequiredMixin, TemplateView):
    template_name = "invoices/internal/invoice_form.html"

    def get(self, request, *args, **kwargs):
        initial = {}
        sale_id = request.GET.get("sale")
        if sale_id:
            initial["sale"] = sale_id
        return self.render_to_response({"form": InvoiceFromSaleForm(initial=initial, user=self.request.user), "ready_sales": ready_sales_for_invoicing_queryset(self.request.user)[:8]})

    def post(self, request, *args, **kwargs):
        form = InvoiceFromSaleForm(request.POST, user=self.request.user)
        if form.is_valid():
            try:
                invoice = create_invoice_from_sale(
                    actor=request.user,
                    sale=form.cleaned_data["sale"],
                    invoice_type=form.cleaned_data["invoice_type"],
                    issue_date=form.cleaned_data["issue_date"],
                    due_date=form.cleaned_data.get("due_date"),
                    notes=form.cleaned_data.get("notes", ""),
                    internal_notes=form.cleaned_data.get("internal_notes", ""),
                )
            except ValidationError as exc:
                form.add_error(None, exc.message if hasattr(exc, "message") else exc)
            else:
                messages.success(request, "Comprobante creado en borrador. Revisa las líneas antes de emitir.")
                return redirect("invoices_internal:detail", pk=invoice.pk)
        return self.render_to_response({"form": form, "ready_sales": ready_sales_for_invoicing_queryset(self.request.user)[:8]})


class InvoiceDetailView(InvoiceAccessMixin, DetailView):
    template_name = "invoices/internal/invoice_detail.html"
    context_object_name = "invoice"

    def get_queryset(self):
        return invoice_detail_queryset(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["lines"] = self.object.lines.all()
        ctx["payments"] = invoice_payments_queryset(self.object)
        ctx["history"] = self.object.status_history.select_related("changed_by")[:20]
        ctx["line_form"] = InvoiceLineForm()
        ctx["payment_form"] = InvoicePaymentApplicationForm(invoice=self.object)
        ctx["action_form"] = InvoiceActionForm()
        ctx["void_form"] = InvoiceActionForm(require_reason=True)
        return ctx


class InvoiceLineCreateView(InvoiceIssueRequiredMixin, View):
    def post(self, request, pk):
        invoice = get_object_or_404(invoice_detail_queryset(request.user), pk=pk)
        form = InvoiceLineForm(request.POST)
        if form.is_valid():
            try:
                add_invoice_line(actor=request.user, invoice=invoice, form=form)
                messages.success(request, "Línea agregada correctamente.")
            except ValidationError as exc:
                messages.error(request, exc.message if hasattr(exc, "message") else str(exc))
        else:
            messages.error(request, "No se pudo agregar la línea. Revisa los datos.")
        return redirect("invoices_internal:detail", pk=invoice.pk)


class InvoicePaymentApplyView(InvoiceIssueRequiredMixin, View):
    def post(self, request, pk):
        invoice = get_object_or_404(invoice_detail_queryset(request.user), pk=pk)
        form = InvoicePaymentApplicationForm(request.POST, invoice=invoice)
        if form.is_valid():
            try:
                apply_payment(actor=request.user, invoice=invoice, amount=form.cleaned_data["amount"], sale_payment=form.cleaned_data.get("sale_payment"), notes=form.cleaned_data.get("notes", ""))
                messages.success(request, "Pago aplicado correctamente.")
            except ValidationError as exc:
                messages.error(request, exc.message if hasattr(exc, "message") else str(exc))
        else:
            messages.error(request, "No se pudo aplicar el pago. Revisa los datos.")
        return redirect("invoices_internal:detail", pk=invoice.pk)


class InvoiceActionView(View):
    """ES: Agrupa el componente «invoice action view» del dominio de facturación y sus reglas relacionadas. Además, aplica autorización en backend, rechaza estados o entradas inválidas.

    EN: Groups the «invoice action view» component and its related rules in the invoices domain. It also enforces server-side authorization, rejects invalid input or state.
    """

    def post(self, request, pk, action):
        """ES: Procesa solicitudes POST de InvoiceActionView aplicando el flujo del dominio de facturación. Además, aplica autorización en backend, rechaza estados o entradas inválidas.

        EN: Processes POST requests on InvoiceActionView using the invoices domain flow. It also enforces server-side authorization, rejects invalid input or state.
        """

        invoice = get_object_or_404(invoice_detail_queryset(request.user), pk=pk)
        if action == "issue":
            if not (request.user.has_perm_code("invoices.issue") or request.user.has_perm_code("invoices.manage")):
                messages.error(request, "No tienes permiso para emitir comprobantes.")
                return redirect("invoices_internal:detail", pk=invoice.pk)
            form = InvoiceActionForm(request.POST)
            if form.is_valid():
                try:
                    issue_invoice(actor=request.user, invoice=invoice, note=form.cleaned_data.get("note", ""))
                    messages.success(request, "Comprobante emitido correctamente.")
                except ValidationError as exc:
                    messages.error(request, exc.message if hasattr(exc, "message") else str(exc))
        elif action == "apply_sale_payments":
            if not (request.user.has_perm_code("invoices.issue") or request.user.has_perm_code("invoices.manage")):
                messages.error(request, "No tienes permiso para aplicar pagos.")
                return redirect("invoices_internal:detail", pk=invoice.pk)
            try:
                created = apply_confirmed_sale_payments(actor=request.user, invoice=invoice)
                messages.success(request, f"Pagos aplicados: {len(created)}.")
            except ValidationError as exc:
                messages.error(request, exc.message if hasattr(exc, "message") else str(exc))
        elif action == "void":
            if not (request.user.has_perm_code("invoices.void") or request.user.has_perm_code("invoices.manage")):
                messages.error(request, "No tienes permiso para anular comprobantes.")
                return redirect("invoices_internal:detail", pk=invoice.pk)
            form = InvoiceActionForm(request.POST, require_reason=True)
            if form.is_valid():
                try:
                    void_invoice(actor=request.user, invoice=invoice, reason=form.cleaned_data.get("reason", ""))
                    messages.success(request, "Comprobante anulado correctamente.")
                except ValidationError as exc:
                    messages.error(request, exc.message if hasattr(exc, "message") else str(exc))
            else:
                messages.error(request, "El motivo de anulación es obligatorio.")
        else:
            messages.error(request, "Acción no válida.")
        return redirect("invoices_internal:detail", pk=invoice.pk)


class InvoicePrintView(InvoiceAccessMixin, DetailView):
    template_name = "invoices/internal/invoice_print.html"
    context_object_name = "invoice"

    def get_queryset(self):
        return invoice_detail_queryset(self.request.user)


class InvoicePdfDownloadView(InvoiceAccessMixin, View):
    def get(self, request, pk):
        invoice = get_object_or_404(invoice_detail_queryset(request.user), pk=pk)
        try:
            document = ensure_invoice_pdf(actor=request.user, invoice=invoice)
        except ValidationError as exc:
            raise Http404(str(exc)) from exc
        handle = open_private_file_or_404(document.file, context="PDF de factura interna")
        register_document_download(actor=request.user, document=document)
        filename = document.original_name or Path(document.file.name).name
        response = FileResponse(handle, as_attachment=True, filename=filename)
        response["Content-Type"] = "application/pdf"
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response
