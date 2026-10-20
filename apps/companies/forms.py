"""ES: Este módulo define formularios y validación de entrada en backend para el dominio de empresa.

EN: This module defines forms and server-side input validation for the companies domain.

Contexto existente / Existing context:
Server-side forms and input validation for the companies domain.
"""

from django import forms
from apps.companies.models import Company
from apps.common.validators import (
    validate_ec_ruc,
    validate_hex_color,
    validate_no_unsafe_control_characters,
    validate_phone_number,
)


class CompanySearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Buscar",
        widget=forms.SearchInput(attrs={"class": "form-control", "placeholder": "Buscar por nombre comercial, razón social o RUC"}),
    )


class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        fields = [
            "legal_name",
            "commercial_name",
            "ruc",
            "email",
            "phone",
            "address",
            "logo",
            "primary_color",
            "secondary_color",
            "is_active",
        ]
        labels = {
            "legal_name": "Razón social",
            "commercial_name": "Nombre comercial",
            "ruc": "RUC",
            "email": "Correo",
            "phone": "Teléfono",
            "address": "Dirección legal",
            "logo": "Logo",
            "primary_color": "Color principal",
            "secondary_color": "Color secundario",
            "is_active": "Empresa activa",
        }
        widgets = {
            "legal_name": forms.TextInput(attrs={"class": "form-control"}),
            "commercial_name": forms.TextInput(attrs={"class": "form-control"}),
            "ruc": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "primary_color": forms.TextInput(attrs={"class": "form-control", "type": "color"}),
            "secondary_color": forms.TextInput(attrs={"class": "form-control", "type": "color"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["ruc"].validators.append(validate_ec_ruc)
        self.fields["phone"].validators.append(validate_phone_number)
        self.fields["phone"].widget.attrs.setdefault("inputmode", "tel")
        for name in ("legal_name", "commercial_name", "address"):
            self.fields[name].validators.append(validate_no_unsafe_control_characters)
        for name in ("primary_color", "secondary_color"):
            self.fields[name].validators.append(validate_hex_color)
