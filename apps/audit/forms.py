"""ES: Este módulo define formularios y validación de entrada en backend para el dominio de auditoría.

EN: This module defines forms and server-side input validation for the audit domain.

Contexto existente / Existing context:
Server-side forms and input validation for the audit domain.
"""

from __future__ import annotations

from django import forms

from apps.accounts.models import User
from apps.accounts.scopes import accessible_branch_ids, accessible_branches_queryset, accessible_users_queryset
from apps.audit.models import AuditLog, SecurityAlert
from apps.branches.models import Branch
from apps.common.form_widgets import make_searchable_select


class AuditFilterForm(forms.Form):
    q = forms.CharField(required=False, label="Buscar", widget=forms.TextInput(attrs={"placeholder": "Acción, objeto, usuario, IP, evento..."}))
    action = forms.CharField(required=False, label="Acción", widget=forms.TextInput(attrs={"placeholder": "Ej. vehicles.update"}))
    category = forms.ChoiceField(required=False, label="Categoría")
    severity = forms.ChoiceField(required=False, label="Severidad")
    result = forms.ChoiceField(required=False, label="Resultado")
    user = forms.ModelChoiceField(required=False, label="Usuario", queryset=User.objects.none())
    branch = forms.ModelChoiceField(required=False, label="Sucursal", queryset=Branch.objects.none())
    object_type = forms.CharField(required=False, label="Tipo de objeto", widget=forms.TextInput(attrs={"placeholder": "Ej. vehicles.vehicle"}))
    ip_address = forms.CharField(required=False, label="IP")
    date_from = forms.DateField(required=False, label="Desde", widget=forms.DateInput(attrs={"type": "date"}))
    date_to = forms.DateField(required=False, label="Hasta", widget=forms.DateInput(attrs={"type": "date"}))

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        permission_code = kwargs.pop("permission_code", "audit.view")
        super().__init__(*args, **kwargs)
        self.fields["category"].choices = [("", "Todas")] + list(AuditLog.Category.choices)
        self.fields["severity"].choices = [("", "Todas")] + list(AuditLog.Severity.choices)
        self.fields["result"].choices = [("", "Todos")] + list(AuditLog.Result.choices)
        branch_ids = accessible_branch_ids(user, permission_codes=(permission_code,))
        self.fields["user"].queryset = (
            User.objects.order_by("username")
            if branch_ids is None
            else accessible_users_queryset(user, permission_codes=(permission_code,)).order_by("username")
        )
        self.fields["branch"].queryset = accessible_branches_queryset(user, permission_codes=(permission_code,))
        self.fields["user"].empty_label = "Todos los usuarios"
        self.fields["branch"].empty_label = "Todas las sucursales"
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        make_searchable_select(self.fields["user"], "Buscar usuario...")
        make_searchable_select(self.fields["branch"], "Buscar sucursal...")


class SecurityAlertFilterForm(forms.Form):
    q = forms.CharField(required=False, label="Buscar", widget=forms.TextInput(attrs={"placeholder": "Código, título, usuario..."}))
    severity = forms.ChoiceField(required=False, label="Severidad")
    status = forms.ChoiceField(required=False, label="Estado")
    branch = forms.ModelChoiceField(required=False, label="Sucursal", queryset=Branch.objects.none())

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["severity"].choices = [("", "Todas")] + list(AuditLog.Severity.choices)
        self.fields["status"].choices = [("", "Todos")] + list(SecurityAlert.Status.choices)
        self.fields["branch"].queryset = accessible_branches_queryset(user, permission_codes=("audit.view",)).order_by("name")
        self.fields["branch"].empty_label = "Todas las sucursales"
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        make_searchable_select(self.fields["branch"], "Buscar sucursal...")


class SecurityAlertResolutionForm(forms.Form):
    status = forms.ChoiceField(label="Nuevo estado", choices=SecurityAlert.Status.choices)
    resolution_notes = forms.CharField(label="Notas de revisión", required=False, widget=forms.Textarea(attrs={"rows": 4}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
