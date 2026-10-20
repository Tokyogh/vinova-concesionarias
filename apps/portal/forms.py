"""ES: Este módulo define formularios y validación de entrada en backend para el dominio de portal cliente.

EN: This module defines forms and server-side input validation for the portal domain.

Contexto existente / Existing context:
Server-side forms and input validation for the portal domain.
"""

from django import forms

from apps.common.validators import (
    validate_human_name,
    validate_no_unsafe_control_characters,
    validate_phone_number,
)
from apps.customers.models import Customer
from apps.documents.models import PrivateDocument
from apps.invoices.models import InvoiceRecord
from apps.notifications.models import CustomerNotificationPreference, NotificationMessage, NotificationRecipient
from apps.post_sales.models import ServiceOrder
from apps.vehicles.models import VehicleLinkCode


class PortalCustomerProfileForm(forms.Form):
    """ES: Valida el contacto editable sin volver obligatorio todo el perfil.

    EN: Validates editable contact data without making the entire profile mandatory.
    """

    phone = forms.CharField(label="Teléfono", max_length=30, required=False, validators=[validate_phone_number], widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "tel", "inputmode": "tel"}))
    whatsapp = forms.CharField(label="WhatsApp", max_length=30, required=False, validators=[validate_phone_number], widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "tel", "inputmode": "tel"}))
    address = forms.CharField(label="Dirección", max_length=220, required=False, widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "street-address"}))
    city = forms.CharField(label="Ciudad", max_length=90, required=False, widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "address-level2"}))
    province = forms.CharField(label="Provincia", max_length=90, required=False, widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "address-level1"}))
    preferred_contact_method = forms.ChoiceField(label="Canal de contacto preferido", choices=Customer.ContactMethod.choices, widget=forms.Select(attrs={"class": "form-control"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["address"].validators.append(validate_no_unsafe_control_characters)
        for name in ("city", "province"):
            self.fields[name].validators.append(validate_human_name)

    def clean(self):
        """ES: Exige solo el dato correspondiente al canal elegido.

        EN: Requires only the data associated with the selected channel.
        """

        cleaned = super().clean()
        preferred = cleaned.get("preferred_contact_method")
        if preferred == Customer.ContactMethod.PHONE and not cleaned.get("phone"):
            self.add_error("phone", "Registra un teléfono para usarlo como canal preferido.")
        elif preferred == Customer.ContactMethod.WHATSAPP and not cleaned.get("whatsapp"):
            self.add_error("whatsapp", "Registra un número de WhatsApp para usarlo como canal preferido.")
        return cleaned


class PortalVehicleSearchForm(forms.Form):
    q = forms.CharField(
        label="Buscar",
        required=False,
        max_length=100,
        widget=forms.SearchInput(
            attrs={"class": "form-control", "placeholder": "Marca, modelo, versión o placa"}
        ),
    )


class PortalDocumentFilterForm(forms.Form):
    q = forms.CharField(
        label="Buscar documentos",
        required=False,
        max_length=100,
        widget=forms.SearchInput(attrs={"class": "form-control", "placeholder": "Título, archivo o vehículo"}),
    )
    document_type = forms.ChoiceField(
        label="Tipo",
        required=False,
        choices=[("", "Todos los tipos"), *PrivateDocument.DocumentType.choices],
        widget=forms.Select(attrs={"class": "form-control"}),
    )


class PortalInvoiceFilterForm(forms.Form):
    q = forms.CharField(
        label="Buscar comprobantes",
        required=False,
        max_length=100,
        widget=forms.SearchInput(attrs={"class": "form-control", "placeholder": "Número de comprobante"}),
    )
    status = forms.ChoiceField(
        label="Estado",
        required=False,
        choices=[("", "Todos los estados"), *InvoiceRecord.Status.choices],
        widget=forms.Select(attrs={"class": "form-control"}),
    )


class PortalNotificationFilterForm(forms.Form):
    q = forms.CharField(
        label="Buscar notificaciones",
        required=False,
        max_length=100,
        widget=forms.SearchInput(attrs={"class": "form-control", "placeholder": "Título o contenido"}),
    )
    message_type = forms.ChoiceField(
        label="Categoría",
        required=False,
        choices=[("", "Todas las categorías"), *NotificationMessage.MessageType.choices],
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    delivery_status = forms.ChoiceField(
        label="Lectura",
        required=False,
        choices=[
            ("", "Leídas y no leídas"),
            (NotificationRecipient.DeliveryStatus.UNREAD, "No leídas"),
            (NotificationRecipient.DeliveryStatus.READ, "Leídas"),
        ],
        widget=forms.Select(attrs={"class": "form-control"}),
    )


class PortalServiceFilterForm(forms.Form):
    q = forms.CharField(
        label="Buscar servicios",
        required=False,
        max_length=100,
        widget=forms.SearchInput(attrs={"class": "form-control", "placeholder": "Orden, vehículo o descripción"}),
    )
    status = forms.ChoiceField(
        label="Estado",
        required=False,
        choices=[("", "Todos los estados"), *ServiceOrder.Status.choices],
        widget=forms.Select(attrs={"class": "form-control"}),
    )


class PortalVehicleRedeemForm(forms.Form):
    code = forms.CharField(
        label="Código de vinculación",
        min_length=19,
        max_length=23,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "autocomplete": "off",
                "autocapitalize": "characters",
                "inputmode": "text",
                "maxlength": "23",
                "placeholder": "VNV-XXXX-XXXX-XXXX-XXXX",
                "data-vnv-code": "",
                "aria-describedby": "vnv-code-help",
            }
        ),
        help_text="Puedes escribir o pegar el código con o sin guiones.",
    )

    def clean_code(self):
        """ES: Normaliza la entrada al contrato exacto emitido por el servidor.

        EN: Normalizes input to the exact contract issued by the server.
        """

        return VehicleLinkCode.normalize_input(self.cleaned_data["code"])


class PortalNotificationPreferenceForm(forms.ModelForm):
    class Meta:
        model = CustomerNotificationPreference
        fields = (
            "invoice_updates",
            "document_updates",
            "service_updates",
            "general_alerts",
            "email_enabled",
        )
        labels = {
            "invoice_updates": "Facturas y comprobantes",
            "document_updates": "Documentos publicados",
            "service_updates": "Cambios en servicios",
            "general_alerts": "Alertas generales",
            "email_enabled": "Permitir correo cuando exista un proveedor configurado",
        }
