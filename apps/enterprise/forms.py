"""ES: Este módulo define formularios y validación de entrada en backend para el dominio de configuración empresarial.

EN: This module defines forms and server-side input validation for the enterprise domain.

Contexto existente / Existing context:
Server-side forms and input validation for the enterprise domain.
"""

from django import forms

from apps.companies.models import Company
from apps.common.validators import (
    validate_ec_ruc,
    validate_hex_color,
    validate_no_unsafe_control_characters,
    validate_phone_number,
)
from apps.enterprise.models import ApprovalPolicy, CompanyPublicSettings


FORM_CONTROL = {"class": "form-control"}
TEXTAREA = {"class": "form-control", "rows": 4}


class CompanyCoreForm(forms.ModelForm):
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
        ]
        labels = {
            "legal_name": "Razón social",
            "commercial_name": "Nombre comercial",
            "ruc": "RUC",
            "email": "Correo corporativo",
            "phone": "Teléfono corporativo",
            "address": "Dirección matriz/legal",
            "logo": "Logo empresarial",
            "primary_color": "Color principal",
            "secondary_color": "Color secundario",
        }
        widgets = {
            "legal_name": forms.TextInput(attrs=FORM_CONTROL),
            "commercial_name": forms.TextInput(attrs=FORM_CONTROL),
            "ruc": forms.TextInput(attrs=FORM_CONTROL),
            "email": forms.EmailInput(attrs=FORM_CONTROL),
            "phone": forms.TextInput(attrs=FORM_CONTROL),
            "address": forms.Textarea(attrs=TEXTAREA),
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


class PublicContactForm(forms.ModelForm):
    website = forms.URLField(
        label="Sitio web", required=False, assume_scheme="https", widget=forms.URLInput(attrs=FORM_CONTROL)
    )
    facebook_url = forms.URLField(
        label="Facebook", required=False, assume_scheme="https", widget=forms.URLInput(attrs=FORM_CONTROL)
    )
    instagram_url = forms.URLField(
        label="Instagram", required=False, assume_scheme="https", widget=forms.URLInput(attrs=FORM_CONTROL)
    )
    linkedin_url = forms.URLField(
        label="LinkedIn", required=False, assume_scheme="https", widget=forms.URLInput(attrs=FORM_CONTROL)
    )
    youtube_url = forms.URLField(
        label="YouTube", required=False, assume_scheme="https", widget=forms.URLInput(attrs=FORM_CONTROL)
    )

    class Meta:
        model = CompanyPublicSettings
        fields = [
            "website",
            "whatsapp",
            "public_email",
            "public_phone",
            "public_address",
            "opening_hours",
            "facebook_url",
            "instagram_url",
            "linkedin_url",
            "youtube_url",
            "show_social_links",
            "enable_public_contact_cta",
        ]
        labels = {
            "website": "Sitio web",
            "whatsapp": "WhatsApp público",
            "public_email": "Correo público",
            "public_phone": "Teléfono público",
            "public_address": "Dirección pública",
            "opening_hours": "Horarios de atención",
            "facebook_url": "Facebook",
            "instagram_url": "Instagram",
            "linkedin_url": "LinkedIn",
            "youtube_url": "YouTube",
            "show_social_links": "Mostrar redes sociales",
            "enable_public_contact_cta": "Mostrar llamados de contacto",
        }
        widgets = {field: forms.TextInput(attrs=FORM_CONTROL) for field in ["whatsapp", "public_email", "public_phone"]}
        widgets.update(
            {"public_address": forms.Textarea(attrs=TEXTAREA), "opening_hours": forms.Textarea(attrs=TEXTAREA)}
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("whatsapp", "public_phone"):
            self.fields[name].validators.append(validate_phone_number)
            self.fields[name].widget.attrs.setdefault("inputmode", "tel")
        for name in ("public_address", "opening_hours"):
            self.fields[name].validators.append(validate_no_unsafe_control_characters)


class PublicSiteForm(forms.ModelForm):
    class Meta:
        model = CompanyPublicSettings
        fields = [
            "hero_eyebrow",
            "hero_title",
            "hero_subtitle",
            "hero_primary_label",
            "hero_secondary_label",
            "catalog_intro_title",
            "catalog_intro_text",
            "attention_title",
            "attention_text",
            "footer_text",
            "show_public_branches",
            "show_vehicle_prices",
            "allow_client_registration",
        ]
        labels = {
            "hero_eyebrow": "Texto pequeño del hero",
            "hero_title": "Título principal",
            "hero_subtitle": "Subtítulo principal",
            "hero_primary_label": "Botón principal",
            "hero_secondary_label": "Botón secundario",
            "catalog_intro_title": "Título del catálogo",
            "catalog_intro_text": "Texto del catálogo",
            "attention_title": "Título de atención",
            "attention_text": "Texto de atención",
            "footer_text": "Texto del footer",
            "show_public_branches": "Mostrar sucursales públicas",
            "show_vehicle_prices": "Mostrar precios de vehículos",
            "allow_client_registration": "Permitir registro público de nuevos clientes",
        }
        widgets = {
            "hero_eyebrow": forms.TextInput(attrs=FORM_CONTROL),
            "hero_title": forms.TextInput(attrs=FORM_CONTROL),
            "hero_subtitle": forms.Textarea(attrs=TEXTAREA),
            "hero_primary_label": forms.TextInput(attrs=FORM_CONTROL),
            "hero_secondary_label": forms.TextInput(attrs=FORM_CONTROL),
            "catalog_intro_title": forms.TextInput(attrs=FORM_CONTROL),
            "catalog_intro_text": forms.Textarea(attrs=TEXTAREA),
            "attention_title": forms.TextInput(attrs=FORM_CONTROL),
            "attention_text": forms.Textarea(attrs=TEXTAREA),
            "footer_text": forms.Textarea(attrs=TEXTAREA),
        }


class LegalSettingsForm(forms.ModelForm):
    class Meta:
        model = CompanyPublicSettings
        fields = ["privacy_policy", "terms_and_conditions", "data_processing_summary"]
        labels = {
            "privacy_policy": "Política de privacidad",
            "terms_and_conditions": "Términos y condiciones",
            "data_processing_summary": "Resumen de tratamiento de datos",
        }
        widgets = {
            "privacy_policy": forms.Textarea(attrs={"class": "form-control", "rows": 8}),
            "terms_and_conditions": forms.Textarea(attrs={"class": "form-control", "rows": 8}),
            "data_processing_summary": forms.Textarea(attrs={"class": "form-control", "rows": 6}),
        }


class ApprovalPolicyForm(forms.ModelForm):
    class Meta:
        model = ApprovalPolicy
        fields = [
            "mode",
            "threshold_amount",
            "threshold_percent",
            "applies_to_roles",
            "requires_reason",
            "notify_supervisors",
            "is_active",
            "notes",
        ]
        labels = {
            "mode": "Modo de autorización",
            "threshold_amount": "Umbral por monto",
            "threshold_percent": "Umbral por porcentaje",
            "applies_to_roles": "Roles afectados",
            "requires_reason": "Solicitar motivo",
            "notify_supervisors": "Notificar supervisores",
            "is_active": "Política activa",
            "notes": "Notas internas",
        }
        widgets = {
            "mode": forms.Select(attrs=FORM_CONTROL),
            "threshold_amount": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "threshold_percent": forms.NumberInput(attrs={"class": "form-control", "step": "0.01"}),
            "applies_to_roles": forms.SelectMultiple(attrs={"class": "form-control", "size": 8}),
            "notes": forms.Textarea(attrs=TEXTAREA),
        }
