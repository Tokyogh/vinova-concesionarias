"""ES: Este módulo define formularios y validación de entrada en backend para el dominio de privacidad.

EN: This module defines forms and server-side input validation for the privacy domain.

Contexto existente / Existing context:
Server-side forms and input validation for the privacy domain.
"""

from django import forms
from django.utils import timezone

from apps.accounts.scopes import accessible_users_queryset, scope_queryset_to_user_branches
from apps.common.validators import (
    validate_human_name,
    validate_no_unsafe_control_characters,
    validate_phone_number,
)
from apps.customers.models import Customer
from apps.privacy.models import DataSubjectRequest, RetentionPolicy


class CookiePreferencesForm(forms.Form):
    """ES: Categorías opcionales sin casillas premarcadas. EN: Optional categories without preselection."""

    preferences = forms.BooleanField(required=False, label="Preferencias de interfaz")
    analytics = forms.BooleanField(required=False, label="Analítica de catálogo")
    external_media = forms.BooleanField(required=False, label="Mapas y contenido externo")
    action = forms.ChoiceField(
        choices=(("save", "Guardar"), ("accept_all", "Aceptar opcionales"), ("reject_optional", "Rechazar opcionales")),
        widget=forms.HiddenInput(),
    )
    next = forms.CharField(required=False, widget=forms.HiddenInput())

    def selected_categories(self):
        action = self.cleaned_data["action"]
        if action == "accept_all":
            return {"preferences": True, "analytics": True, "external_media": True}
        if action == "reject_optional":
            return {"preferences": False, "analytics": False, "external_media": False}
        return {
            "preferences": bool(self.cleaned_data.get("preferences")),
            "analytics": bool(self.cleaned_data.get("analytics")),
            "external_media": bool(self.cleaned_data.get("external_media")),
        }


class PublicDataSubjectRequestForm(forms.ModelForm):
    website = forms.CharField(required=False, widget=forms.HiddenInput())
    privacy_acknowledgement = forms.BooleanField(label="Confirmo que los datos son míos y acepto ser contactado para verificar mi identidad.")

    class Meta:
        model = DataSubjectRequest
        fields = ["request_type", "requester_name", "requester_email", "requester_phone", "identification_hint", "description"]
        labels = {
            "request_type": "Tipo de solicitud", "requester_name": "Nombre completo", "requester_email": "Correo",
            "requester_phone": "Teléfono", "identification_hint": "Últimos dígitos de identificación (opcional)",
            "description": "Describe tu solicitud",
        }
        widgets = {"description": forms.Textarea(attrs={"rows": 5})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["requester_name"].validators.append(validate_human_name)
        self.fields["requester_phone"].validators.append(validate_phone_number)
        self.fields["requester_phone"].widget.attrs.update({"autocomplete": "tel", "inputmode": "tel"})
        self.fields["description"].validators.append(validate_no_unsafe_control_characters)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Solicitud no válida.")
        return ""

    def clean(self):
        cleaned = super().clean()
        if not (cleaned.get("requester_email") or cleaned.get("requester_phone")):
            self.add_error("requester_email", "Registra correo o teléfono para verificar la identidad.")
        return cleaned

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.status = DataSubjectRequest.Status.IDENTITY_PENDING
        instance.received_at = timezone.now()
        if commit:
            instance.save()
        return instance


class InternalDataSubjectRequestForm(forms.ModelForm):
    class Meta:
        model = DataSubjectRequest
        fields = [
            "request_type", "status", "customer", "requester_name", "requester_email", "requester_phone",
            "identification_hint", "description", "due_at", "assigned_to", "resolution", "legal_hold_reason",
        ]
        widgets = {"description": forms.Textarea(attrs={"rows": 4}), "resolution": forms.Textarea(attrs={"rows": 4}), "legal_hold_reason": forms.Textarea(attrs={"rows": 3}), "due_at": forms.DateTimeInput(attrs={"type": "datetime-local"})}

    def __init__(self, *args, user=None, permission_code="privacy.manage", **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["requester_name"].validators.append(validate_human_name)
        self.fields["requester_phone"].validators.append(validate_phone_number)
        self.fields["requester_phone"].widget.attrs.update({"autocomplete": "tel", "inputmode": "tel"})
        for name in ("description", "resolution", "legal_hold_reason"):
            self.fields[name].validators.append(validate_no_unsafe_control_characters)
        self.fields["customer"].queryset = scope_queryset_to_user_branches(
            Customer.objects.filter(is_deleted=False),
            user=user,
            permission_codes=(permission_code,),
            branch_lookup="assigned_branch",
        ).order_by("business_name", "first_name", "last_name")
        self.fields["assigned_to"].queryset = accessible_users_queryset(
            user,
            permission_codes=(permission_code,),
        )
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class RequestStatusForm(forms.Form):
    status = forms.ChoiceField(label="Nuevo estado", choices=DataSubjectRequest.Status.choices)
    resolution = forms.CharField(required=False, label="Resolución / nota", widget=forms.Textarea(attrs={"rows": 4}))
    legal_hold_reason = forms.CharField(required=False, label="Motivo de retención legal", widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class RetentionPolicyForm(forms.ModelForm):
    class Meta:
        model = RetentionPolicy
        fields = ["code", "name", "data_category", "retention_days", "action", "is_active", "requires_legal_review", "description", "next_review_at"]
        widgets = {"description": forms.Textarea(attrs={"rows": 4}), "next_review_at": forms.DateInput(attrs={"type": "date"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
