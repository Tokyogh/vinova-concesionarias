"""ES: Este módulo define formularios y validación de entrada en backend para el dominio de ventas.

EN: This module defines forms and server-side input validation for the sales domain.

Contexto existente / Existing context:
Server-side forms and input validation for the sales domain.
"""

from __future__ import annotations

from decimal import Decimal

from django import forms
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.scopes import accessible_branches_queryset
from apps.branches.models import Branch
from apps.customers.models import Customer
from apps.inventory.models import InventoryItem
from apps.sales.models import SaleLine, SalePayment, SaleRecord
from apps.vehicles.models import Vehicle
from apps.common.form_widgets import configure_accessible_filter_fields, make_searchable_select


class SaleSearchForm(forms.Form):
    q = forms.CharField(required=False, label="Buscar", widget=forms.TextInput(attrs={"placeholder": "Número, cliente, cédula/RUC, VIN, placa, vehículo..."}))
    status = forms.ChoiceField(required=False, label="Estado")
    kind = forms.ChoiceField(required=False, label="Tipo")
    branch = forms.ModelChoiceField(required=False, label="Sucursal", queryset=Branch.objects.none())
    sort = forms.ChoiceField(required=False, label="Orden", choices=[
        ("", "Más recientes"), ("oldest", "Más antiguos"),
        ("total_desc", "Total: mayor a menor"), ("total_asc", "Total: menor a mayor"),
    ])

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = [("", "Todos los estados")] + list(SaleRecord.Status.choices)
        self.fields["kind"].choices = [("", "Todos los tipos")] + list(SaleRecord.Kind.choices)
        self.fields["branch"].queryset = accessible_branches_queryset(
            user, permission_codes=("sales.quote", "sales.reserve", "sales.sell")
        )
        self.fields["branch"].empty_label = "Todas las sucursales"
        configure_accessible_filter_fields(self.fields)


class SaleRecordForm(forms.ModelForm):
    """ES: Agrupa el componente «sale record form» del dominio de ventas y sus reglas relacionadas.

    EN: Groups the «sale record form» component and its related rules in the sales domain.
    """

    class Meta:
        model = SaleRecord
        fields = [
            "kind",
            "customer",
            "branch",
            "advisor",
            "vehicle",
            "source",
            "vehicle_price",
            "vehicle_discount",
            "tax_rate",
            "valid_until",
            "reserved_until",
            "notes",
            "internal_notes",
        ]
        labels = {
            "kind": "Tipo de operación",
            "customer": "Cliente",
            "branch": "Sucursal",
            "advisor": "Asesor responsable",
            "vehicle": "Vehículo asociado",
            "source": "Origen",
            "vehicle_price": "Precio del vehículo",
            "vehicle_discount": "Descuento del vehículo",
            "tax_rate": "IVA (%)",
            "valid_until": "Cotización válida hasta",
            "reserved_until": "Reserva vigente hasta",
            "notes": "Notas visibles / comerciales",
            "internal_notes": "Notas internas",
        }
        widgets = {
            "valid_until": forms.DateInput(attrs={"type": "date"}),
            "reserved_until": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
            "internal_notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["customer"].queryset = Customer.objects.filter(is_deleted=False).order_by("business_name", "first_name", "last_name")
        self.fields["branch"].queryset = Branch.objects.filter(is_active=True).order_by("company__commercial_name", "name")
        self.fields["advisor"].queryset = User.objects.filter(is_active=True).order_by("first_name", "last_name", "username")
        self.fields["advisor"].required = False
        self.fields["advisor"].empty_label = "Sin asesor específico"
        self.fields["vehicle"].queryset = Vehicle.objects.filter(is_deleted=False).exclude(status__in=[Vehicle.Status.SOLD, Vehicle.Status.ARCHIVED]).select_related("brand", "model", "model__brand", "branch").order_by("brand__name", "model__name", "year")
        self.fields["vehicle"].required = False
        self.fields["vehicle"].empty_label = "Sin vehículo asociado todavía"
        make_searchable_select(self.fields["customer"], "Buscar cliente por nombre, cédula/RUC o correo...")
        make_searchable_select(self.fields["branch"], "Buscar sucursal...")
        make_searchable_select(self.fields["advisor"], "Buscar asesor...")
        make_searchable_select(self.fields["vehicle"], "Buscar vehículo por marca, modelo, VIN o placa...")
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        vehicle = cleaned.get("vehicle")
        branch = cleaned.get("branch")
        if vehicle and branch and vehicle.branch_id and vehicle.branch_id != branch.id:
            self.add_error("vehicle", "El vehículo seleccionado pertenece a otra sucursal.")
        if vehicle and not cleaned.get("vehicle_price"):
            cleaned["vehicle_price"] = vehicle.price or Decimal("0.00")
        if cleaned.get("reserved_until") and cleaned["reserved_until"] <= timezone.now():
            self.add_error("reserved_until", "La fecha de reserva debe ser futura.")
        return cleaned


class SaleLineForm(forms.ModelForm):
    class Meta:
        model = SaleLine
        fields = ["item", "description", "quantity", "unit_price", "discount_amount", "notes"]
        labels = {"item": "Artículo / servicio", "description": "Descripción", "quantity": "Cantidad", "unit_price": "Precio unitario", "discount_amount": "Descuento", "notes": "Notas"}
        widgets = {"notes": forms.TextInput(attrs={"placeholder": "Opcional"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["item"].queryset = InventoryItem.objects.filter(is_deleted=False, status=InventoryItem.Status.ACTIVE).order_by("sku", "name")
        self.fields["item"].required = False
        self.fields["item"].empty_label = "Sin artículo del inventario"
        make_searchable_select(self.fields["item"], "Buscar artículo por SKU o nombre...")
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        item = cleaned.get("item")
        description = (cleaned.get("description") or "").strip()
        if item and not description:
            cleaned["description"] = item.name
        if item and not cleaned.get("unit_price"):
            cleaned["unit_price"] = item.price
        if not item and not description:
            self.add_error("description", "La línea requiere una descripción si no eliges un artículo.")
        return cleaned


class SalePaymentForm(forms.ModelForm):
    class Meta:
        model = SalePayment
        fields = ["method", "status", "amount", "reference", "paid_at", "notes"]
        labels = {"method": "Método", "status": "Estado", "amount": "Monto", "reference": "Referencia", "paid_at": "Fecha de pago", "notes": "Notas"}
        widgets = {"paid_at": forms.DateTimeInput(attrs={"type": "datetime-local"}), "notes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = [
            choice for choice in SalePayment.Status.choices if choice[0] != SalePayment.Status.VOID
        ]
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class SaleActionForm(forms.Form):
    note = forms.CharField(label="Nota interna", required=False, widget=forms.Textarea(attrs={"rows": 3, "placeholder": "Motivo, observación o condición comercial..."}))
    reserved_until = forms.DateTimeField(label="Reservar hasta", required=False, widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))

    def __init__(self, *args, **kwargs):
        require_reservation_date = kwargs.pop("require_reservation_date", False)
        super().__init__(*args, **kwargs)
        self.require_reservation_date = require_reservation_date
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_reserved_until(self):
        value = self.cleaned_data.get("reserved_until")
        if self.require_reservation_date and not value:
            raise forms.ValidationError("Define hasta cuándo se mantiene la reserva.")
        if value and value <= timezone.now():
            raise forms.ValidationError("La reserva debe vencer en una fecha futura.")
        return value
