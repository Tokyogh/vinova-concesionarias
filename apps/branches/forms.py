"""ES: Este módulo define formularios y validación de entrada en backend para el dominio de sucursales.

EN: This module defines forms and server-side input validation for the branches domain.

Contexto existente / Existing context:
Formularios y validación de entradas para sedes.

Server-side forms and input validation for the branches domain.
"""

from django import forms
from apps.branches.models import Branch
from apps.common.validators import (
    validate_human_name,
    validate_no_unsafe_control_characters,
    validate_phone_number,
)


class BranchSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Buscar",
        widget=forms.SearchInput(attrs={"class": "form-control", "placeholder": "Buscar por nombre, código, ciudad o empresa"}),
    )
    branch_type = forms.ChoiceField(
        required=False,
        label="Tipo",
        choices=[("", "Todos los tipos")] + list(Branch.BranchType.choices),
        widget=forms.Select(attrs={"class": "form-control"}),
    )


class BranchForm(forms.ModelForm):
    """ES: Agrupa el componente «branch form» del dominio de sucursales y sus reglas relacionadas.

    EN: Groups the «branch form» component and its related rules in the branches domain.
    """

    website_url = forms.URLField(
        required=False,
        assume_scheme="https",
        label="Sitio web público",
        help_text="Dirección HTTPS o HTTP completa del sitio oficial de la sede.",
        widget=forms.URLInput(attrs={"class": "form-control", "placeholder": "https://www.ejemplo.com"}),
    )
    services_text = forms.CharField(
        required=False,
        label="Servicios públicos",
        help_text="Un servicio por línea o separados por comas. Se muestran hasta seis.",
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )

    class Meta:
        model = Branch
        fields = [
            "company", "name", "code", "branch_type", "city", "province", "address",
            "phone", "email", "description", "opening_hours", "photo", "website_url",
            "latitude", "longitude",
            "is_public", "is_active",
        ]
        labels = {
            "company": "Empresa",
            "name": "Nombre",
            "code": "Código interno",
            "branch_type": "Tipo de sede",
            "city": "Ciudad",
            "province": "Provincia",
            "address": "Dirección",
            "phone": "Teléfono",
            "email": "Correo",
            "description": "Descripción pública",
            "opening_hours": "Horario de atención",
            "photo": "Fotografía pública",
            "website_url": "Sitio web público",
            "latitude": "Latitud",
            "longitude": "Longitud",
            "is_public": "Visible públicamente",
            "is_active": "Sucursal activa",
        }
        help_texts = {
            "code": "Usa un código corto y estable, por ejemplo QUITO-NORTE o GYE-CENTRO.",
            "is_public": "Solo las sedes públicas deberían mostrarse en páginas comerciales o catálogos externos.",
            "photo": "Imagen JPG, PNG o WEBP. Se publicará únicamente cuando la sede esté activa y visible.",
            "website_url": "Dirección HTTPS o HTTP completa del sitio oficial de la sede.",
            "latitude": "Coordenada entre -90 y 90. Déjala vacía si aún no fue verificada.",
            "longitude": "Coordenada entre -180 y 180. Déjala vacía si aún no fue verificada.",
        }
        widgets = {
            "company": forms.Select(attrs={"class": "form-control"}),
            "name": forms.TextInput(attrs={"class": "form-control"}),
            "code": forms.TextInput(attrs={"class": "form-control"}),
            "branch_type": forms.Select(attrs={"class": "form-control"}),
            "city": forms.TextInput(attrs={"class": "form-control"}),
            "province": forms.TextInput(attrs={"class": "form-control"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": 3}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 4}),
            "opening_hours": forms.TextInput(attrs={"class": "form-control"}),
            "photo": forms.ClearableFileInput(attrs={"class": "form-control", "accept": "image/jpeg,image/png,image/webp"}),
            "latitude": forms.NumberInput(attrs={"class": "form-control", "step": "0.000001"}),
            "longitude": forms.NumberInput(attrs={"class": "form-control", "step": "0.000001"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("city", "province"):
            self.fields[name].validators.append(validate_human_name)
        self.fields["phone"].validators.append(validate_phone_number)
        self.fields["phone"].widget.attrs.setdefault("inputmode", "tel")
        for name in ("name", "address", "description", "opening_hours"):
            self.fields[name].validators.append(validate_no_unsafe_control_characters)
        if self.instance and self.instance.pk:
            values = self.instance.services if isinstance(self.instance.services, list) else []
            self.fields["services_text"].initial = "\n".join(str(value) for value in values)

    def clean_services_text(self):
        raw = self.cleaned_data.get("services_text", "")
        values = []
        for item in raw.replace(";", "\n").replace(",", "\n").splitlines():
            value = item.strip()
            if value and value not in values:
                values.append(value[:80])
        return values[:12]

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.services = self.cleaned_data.get("services_text", [])
        if commit:
            instance.save()
            self.save_m2m()
        return instance
