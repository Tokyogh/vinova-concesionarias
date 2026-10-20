"""ES: Este módulo define formularios y validación de entrada en backend para el dominio de reportes.

EN: This module defines forms and server-side input validation for the reports domain.

Contexto existente / Existing context:
Server-side forms and input validation for the reports domain.
"""

from __future__ import annotations

from django import forms
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.scopes import accessible_branches_queryset, accessible_users_queryset, scope_queryset_to_user_branches
from apps.branches.models import Branch
from apps.inventory.models import InventoryCategory
from apps.sales.models import SaleRecord
from apps.vehicles.models import Vehicle


REPORT_PERMISSION_CODES = ("reports.view",)


class ReportFilterForm(forms.Form):
    """ES: Agrupa el componente «report filter form» del dominio de reportes y sus reglas relacionadas. Además, rechaza estados o entradas inválidas.

    EN: Groups the «report filter form» component and its related rules in the reports domain. It also rejects invalid input or state.
    """

    start_date = forms.DateField(
        required=False,
        label="Desde",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    end_date = forms.DateField(
        required=False,
        label="Hasta",
        widget=forms.DateInput(attrs={"type": "date", "class": "form-control"}),
    )
    branch = forms.ModelChoiceField(
        required=False,
        label="Sucursal",
        queryset=Branch.objects.none(),
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    seller = forms.ModelChoiceField(
        required=False,
        label="Vendedor",
        queryset=User.objects.none(),
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    sale_status = forms.ChoiceField(
        required=False,
        label="Estado comercial",
        choices=[("", "Todos los estados comerciales")] + list(SaleRecord.Status.choices),
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    vehicle = forms.ModelChoiceField(
        required=False,
        label="Vehículo",
        queryset=Vehicle.objects.none(),
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    category = forms.ModelChoiceField(
        required=False,
        label="Categoría",
        queryset=InventoryCategory.objects.none(),
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    q = forms.CharField(
        required=False,
        label="Buscar",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Cliente, factura, VIN, SKU, usuario..."}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["branch"].queryset = accessible_branches_queryset(
            user,
            permission_codes=REPORT_PERMISSION_CODES,
        )
        self.fields["seller"].queryset = accessible_users_queryset(
            user,
            permission_codes=REPORT_PERMISSION_CODES,
        )
        self.fields["vehicle"].queryset = scope_queryset_to_user_branches(
            Vehicle.objects.filter(is_deleted=False).select_related("brand", "model", "model__brand", "branch"),
            user=user,
            permission_codes=REPORT_PERMISSION_CODES,
        ).order_by("brand__name", "model__name", "year")
        self.fields["category"].queryset = InventoryCategory.objects.filter(is_active=True).order_by("name")
        self.fields["branch"].empty_label = "Todas las sucursales permitidas"
        self.fields["seller"].empty_label = "Todos los vendedores permitidos"
        self.fields["vehicle"].empty_label = "Todos los vehículos permitidos"
        self.fields["category"].empty_label = "Todas las categorías"

    def clean(self):
        cleaned = super().clean()
        today = timezone.localdate()
        start = cleaned.get("start_date")
        end = cleaned.get("end_date")
        if not start:
            start = today.replace(day=1)
        if not end:
            end = today
        if start > end:
            raise forms.ValidationError("La fecha desde no puede ser posterior a la fecha hasta.")
        cleaned["start_date"] = start
        cleaned["end_date"] = end
        return cleaned
