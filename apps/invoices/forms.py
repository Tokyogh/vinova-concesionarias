"""ES: Este módulo define formularios y validación de entrada en backend para el dominio de facturación.

EN: This module defines forms and server-side input validation for the invoices domain.

Contexto existente / Existing context:
Server-side forms and input validation for the invoices domain.
"""

from __future__ import annotations

from django import forms
from django.utils import timezone

from apps.branches.models import Branch
from apps.common.form_widgets import make_searchable_select
from apps.accounts.scopes import accessible_branches_queryset
from apps.invoices.models import InvoiceLine, InvoiceRecord
from apps.invoices.selectors import INVOICE_SCOPE_PERMISSIONS, ready_sales_for_invoicing_queryset
from apps.sales.models import SalePayment, SaleRecord


class InvoiceSearchForm(forms.Form):
    q = forms.CharField(required=False, label="Buscar", widget=forms.TextInput(attrs={"placeholder": "Número, cliente, documento, autorización, venta..."}))
    status = forms.ChoiceField(required=False, label="Estado")
    invoice_type = forms.ChoiceField(required=False, label="Tipo")
    branch = forms.ModelChoiceField(required=False, label="Sucursal", queryset=Branch.objects.none())
    sort = forms.ChoiceField(required=False, label="Orden", choices=[
        ("", "Más recientes"), ("oldest", "Más antiguos"),
        ("total_desc", "Total: mayor a menor"), ("due_asc", "Vencimiento próximo"),
    ])

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = [("", "Todos los estados")] + list(InvoiceRecord.Status.choices)
        self.fields["invoice_type"].choices = [("", "Todos los tipos")] + list(InvoiceRecord.InvoiceType.choices)
        if user is not None:
            self.fields["branch"].queryset = accessible_branches_queryset(user, permission_codes=INVOICE_SCOPE_PERMISSIONS)
        else:
            self.fields["branch"].queryset = Branch.objects.filter(is_active=True).order_by("company__commercial_name", "name")
        self.fields["branch"].empty_label = "Todas las sucursales"
        make_searchable_select(self.fields["branch"], "Buscar sucursal...")
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class InvoiceFromSaleForm(forms.Form):
    sale = forms.ModelChoiceField(label="Operación comercial", queryset=SaleRecord.objects.none())
    invoice_type = forms.ChoiceField(label="Tipo", choices=InvoiceRecord.InvoiceType.choices, initial=InvoiceRecord.InvoiceType.INVOICE)
    issue_date = forms.DateField(label="Fecha de emisión", initial=timezone.localdate, widget=forms.DateInput(attrs={"type": "date"}))
    due_date = forms.DateField(label="Fecha de vencimiento", required=False, widget=forms.DateInput(attrs={"type": "date"}))
    notes = forms.CharField(label="Notas visibles", required=False, widget=forms.Textarea(attrs={"rows": 3}))
    internal_notes = forms.CharField(label="Notas internas", required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["sale"].queryset = ready_sales_for_invoicing_queryset(user)
        else:
            self.fields["sale"].queryset = ready_sales_for_invoicing_queryset(None)
        make_searchable_select(self.fields["sale"], "Buscar venta/cotización por número, cliente o vehículo...")
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        issue_date = cleaned.get("issue_date")
        due_date = cleaned.get("due_date")
        if issue_date and due_date and due_date < issue_date:
            self.add_error("due_date", "El vencimiento no puede ser anterior a la emisión.")
        return cleaned


class InvoiceLineForm(forms.ModelForm):
    class Meta:
        model = InvoiceLine
        fields = ["description", "quantity", "unit_price", "discount_amount", "tax_rate"]
        labels = {"description": "Descripción", "quantity": "Cantidad", "unit_price": "Precio unitario", "discount_amount": "Descuento", "tax_rate": "IVA (%)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class InvoicePaymentApplicationForm(forms.Form):
    sale_payment = forms.ModelChoiceField(label="Pago comercial", required=False, queryset=SalePayment.objects.none())
    amount = forms.DecimalField(label="Monto a aplicar", max_digits=12, decimal_places=2)
    notes = forms.CharField(label="Notas", required=False, widget=forms.TextInput(attrs={"placeholder": "Referencia u observación"}))

    def __init__(self, *args, **kwargs):
        invoice = kwargs.pop("invoice", None)
        super().__init__(*args, **kwargs)
        if invoice and invoice.sale_id:
            self.fields["sale_payment"].queryset = invoice.sale.payments.filter(status=SalePayment.Status.CONFIRMED).order_by("-paid_at")
        else:
            self.fields["sale_payment"].queryset = SalePayment.objects.none()
        self.fields["sale_payment"].empty_label = "Pago manual / sin pago comercial"
        make_searchable_select(self.fields["sale_payment"], "Buscar pago confirmado...")
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        sale_payment = cleaned.get("sale_payment")
        amount = cleaned.get("amount")
        if sale_payment and amount and amount > sale_payment.amount:
            self.add_error("amount", "No puedes aplicar más que el monto del pago seleccionado.")
        return cleaned


class InvoiceActionForm(forms.Form):
    note = forms.CharField(label="Nota", required=False, widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Observación interna..."}))
    reason = forms.CharField(label="Motivo", required=False, widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Motivo de anulación..."}))

    def __init__(self, *args, require_reason=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.require_reason = require_reason
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_reason(self):
        value = self.cleaned_data.get("reason", "")
        if self.require_reason and not value.strip():
            raise forms.ValidationError("El motivo es obligatorio.")
        return value
