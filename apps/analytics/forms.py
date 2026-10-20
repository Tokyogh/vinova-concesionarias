"""ES: Este módulo define formularios y validación de entrada en backend para el dominio de analítica.

EN: This module defines forms and server-side input validation for the analytics domain.

Contexto existente / Existing context:
Server-side forms and input validation for the analytics domain.
"""

from django import forms
from django.utils import timezone

from apps.accounts.scopes import accessible_branches_queryset, accessible_users_queryset
from apps.accounts.models import User
from apps.branches.models import Branch
from apps.leads.models import Lead


class CommercialAnalyticsFilterForm(forms.Form):
    start_date = forms.DateField(required=False, label="Desde", widget=forms.DateInput(attrs={"type": "date"}))
    end_date = forms.DateField(required=False, label="Hasta", widget=forms.DateInput(attrs={"type": "date"}))
    branch = forms.ModelChoiceField(required=False, label="Sucursal", queryset=Branch.objects.none())
    advisor = forms.ModelChoiceField(required=False, label="Asesor", queryset=User.objects.none())
    source = forms.ChoiceField(required=False, label="Origen", choices=[("", "Todos los orígenes")] + list(Lead.Source.choices))

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        permission_codes = kwargs.pop("permission_codes", ("analytics.view",))
        super().__init__(*args, **kwargs)
        self.fields["branch"].queryset = accessible_branches_queryset(
            user, permission_codes=permission_codes
        )
        self.fields["advisor"].queryset = accessible_users_queryset(
            user, permission_codes=permission_codes
        )
        self.fields["branch"].empty_label = "Todas las sucursales"
        self.fields["advisor"].empty_label = "Todos los asesores"
        if not self.is_bound:
            today = timezone.localdate()
            self.fields["start_date"].initial = today.replace(day=1)
            self.fields["end_date"].initial = today
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("start_date") and cleaned.get("end_date") and cleaned["start_date"] > cleaned["end_date"]:
            self.add_error("end_date", "La fecha final debe ser posterior a la inicial.")
        return cleaned
