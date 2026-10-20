"""ES: Este módulo define formularios y validación de entrada en backend para el dominio de configuración SRI heredada.

EN: This module defines forms and server-side input validation for the sri integration domain.

Contexto existente / Existing context:
Server-side forms and input validation for the sri integration domain.
"""

from django import forms

from apps.sri_integration.models import SriConfiguration, SriEstablishment, SriSequence

FORM_CONTROL = {"class": "form-control"}
TEXTAREA = {"class": "form-control", "rows": 4}


class SriConfigurationForm(forms.ModelForm):
    """ES: Agrupa el componente «sri configuration form» del dominio de configuración SRI heredada y sus reglas relacionadas. Además, rechaza estados o entradas inválidas.

    EN: Groups the «sri configuration form» component and its related rules in the sri integration domain. It also rejects invalid input or state.
    """

    class Meta:
        model = SriConfiguration
        fields = [
            "ruc",
            "legal_name",
            "commercial_name",
            "matrix_address",
            "environment",
            "status",
            "emission_type",
            "accounting_required",
            "special_taxpayer_resolution",
            "withholding_agent_resolution",
            "taxpayer_regime",
            "electronic_signature_provider",
            "certificate_file",
            "certificate_password_reference",
            "certificate_expires_at",
            "technical_contact_name",
            "technical_contact_email",
            "notes",
        ]
        labels = {
            "ruc": "RUC",
            "legal_name": "Razón social SRI",
            "commercial_name": "Nombre comercial SRI",
            "matrix_address": "Dirección matriz",
            "environment": "Ambiente",
            "status": "Estado de configuración",
            "emission_type": "Tipo de emisión",
            "accounting_required": "Obligado a llevar contabilidad",
            "special_taxpayer_resolution": "Resolución contribuyente especial",
            "withholding_agent_resolution": "Resolución agente de retención",
            "taxpayer_regime": "Régimen tributario",
            "electronic_signature_provider": "Proveedor de firma electrónica",
            "certificate_file": "Certificado electrónico (.p12/.pfx)",
            "certificate_password_reference": "Referencia segura de clave",
            "certificate_expires_at": "Vencimiento del certificado",
            "technical_contact_name": "Contacto técnico",
            "technical_contact_email": "Correo técnico",
            "notes": "Notas internas",
        }
        widgets = {
            "ruc": forms.TextInput(attrs=FORM_CONTROL),
            "legal_name": forms.TextInput(attrs=FORM_CONTROL),
            "commercial_name": forms.TextInput(attrs=FORM_CONTROL),
            "matrix_address": forms.Textarea(attrs=TEXTAREA),
            "environment": forms.Select(attrs=FORM_CONTROL),
            "status": forms.Select(attrs=FORM_CONTROL),
            "emission_type": forms.TextInput(attrs=FORM_CONTROL),
            "special_taxpayer_resolution": forms.TextInput(attrs=FORM_CONTROL),
            "withholding_agent_resolution": forms.TextInput(attrs=FORM_CONTROL),
            "taxpayer_regime": forms.TextInput(attrs=FORM_CONTROL),
            "electronic_signature_provider": forms.TextInput(attrs=FORM_CONTROL),
            "certificate_password_reference": forms.TextInput(attrs=FORM_CONTROL),
            "certificate_expires_at": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "technical_contact_name": forms.TextInput(attrs=FORM_CONTROL),
            "technical_contact_email": forms.EmailInput(attrs=FORM_CONTROL),
            "notes": forms.Textarea(attrs=TEXTAREA),
        }

    def clean_ruc(self):
        ruc = (self.cleaned_data.get("ruc") or "").strip()
        if len(ruc) != 13 or not ruc.isdigit():
            raise forms.ValidationError("El RUC debe contener exactamente 13 dígitos.")
        return ruc


class SriEstablishmentForm(forms.ModelForm):
    class Meta:
        model = SriEstablishment
        fields = ["establishment_code", "emission_point_code", "name", "address", "branch", "is_default", "is_active"]
        labels = {"establishment_code": "Establecimiento", "emission_point_code": "Punto de emisión", "name": "Nombre", "address": "Dirección", "branch": "Sucursal relacionada", "is_default": "Predeterminado", "is_active": "Activo"}
        widgets = {"establishment_code": forms.TextInput(attrs=FORM_CONTROL), "emission_point_code": forms.TextInput(attrs=FORM_CONTROL), "name": forms.TextInput(attrs=FORM_CONTROL), "address": forms.Textarea(attrs=TEXTAREA), "branch": forms.Select(attrs=FORM_CONTROL)}

    def clean_establishment_code(self):
        return self.cleaned_data["establishment_code"].zfill(3)[-3:]

    def clean_emission_point_code(self):
        return self.cleaned_data["emission_point_code"].zfill(3)[-3:]


class SriSequenceForm(forms.ModelForm):
    class Meta:
        model = SriSequence
        fields = ["establishment", "document_type", "current_number", "start_number", "max_number", "is_active", "notes"]
        labels = {"establishment": "Establecimiento/punto", "document_type": "Tipo de documento", "current_number": "Número actual", "start_number": "Número inicial", "max_number": "Número máximo", "is_active": "Activa", "notes": "Notas"}
        widgets = {"establishment": forms.Select(attrs=FORM_CONTROL), "document_type": forms.Select(attrs=FORM_CONTROL), "current_number": forms.NumberInput(attrs=FORM_CONTROL), "start_number": forms.NumberInput(attrs=FORM_CONTROL), "max_number": forms.NumberInput(attrs=FORM_CONTROL), "notes": forms.Textarea(attrs=TEXTAREA)}

    def __init__(self, *args, configuration=None, **kwargs):
        super().__init__(*args, **kwargs)
        if configuration:
            self.fields["establishment"].queryset = configuration.establishments.filter(is_active=True)
