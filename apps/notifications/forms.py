"""ES: Este módulo define formularios y validación de entrada en backend para el dominio de notificaciones.

EN: This module defines forms and server-side input validation for the notifications domain.

Contexto existente / Existing context:
Server-side forms and input validation for the notifications domain.
"""

from __future__ import annotations

from django import forms

from apps.accounts.models import User
from apps.accounts.scopes import accessible_branch_ids, accessible_branches_queryset, accessible_users_queryset, scope_queryset_to_user_branches
from apps.branches.models import Branch
from apps.customers.models import Customer
from apps.documents.models import PrivateDocument
from apps.notifications.models import Campaign, NotificationMessage, NotificationRecipient, NotificationTemplate
from apps.sales.models import SaleRecord
from apps.vehicles.models import Vehicle, VehicleBrand, VehicleModel


def _searchable(widget, placeholder="Escribe para buscar en la lista..."):
    widget.attrs.setdefault("class", "form-control")
    widget.attrs["data-searchable-select"] = "true"
    widget.attrs["data-search-placeholder"] = placeholder
    return widget


class NotificationSearchForm(forms.Form):
    q = forms.CharField(required=False, label="Buscar", widget=forms.TextInput(attrs={"placeholder": "Título, texto, remitente, cliente, vehículo, venta..."}))
    message_type = forms.ChoiceField(required=False, label="Tipo")
    priority = forms.ChoiceField(required=False, label="Prioridad")
    branch = forms.ModelChoiceField(required=False, label="Sucursal", queryset=Branch.objects.none())

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["message_type"].choices = [("", "Todos los tipos")] + list(NotificationMessage.MessageType.choices)
        self.fields["priority"].choices = [("", "Todas las prioridades")] + list(NotificationMessage.Priority.choices)
        self.fields["branch"].queryset = accessible_branches_queryset(user, permission_codes=("notifications.send",))
        self.fields["branch"].empty_label = "Todas las sucursales"
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        _searchable(self.fields["branch"].widget, "Buscar sucursal...")


class NotificationInboxSearchForm(forms.Form):
    q = forms.CharField(required=False, label="Buscar", widget=forms.TextInput(attrs={"placeholder": "Buscar en tus mensajes..."}))
    status = forms.ChoiceField(required=False, label="Estado")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = [("", "Todos")] + list(NotificationRecipient.DeliveryStatus.choices)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class NotificationMessageForm(forms.ModelForm):
    """Validate internal/customer recipients and message delivery options."""

    recipient_users = forms.ModelMultipleChoiceField(
        label="Usuarios internos destinatarios",
        required=False,
        queryset=User.objects.none(),
        widget=forms.SelectMultiple(attrs={"size": 8}),
        help_text="Busca por nombre, usuario o correo. Puedes seleccionar varios.",
    )
    recipient_customers = forms.ModelMultipleChoiceField(
        label="Clientes destinatarios",
        required=False,
        queryset=Customer.objects.none(),
        widget=forms.SelectMultiple(attrs={"size": 8}),
        help_text="Busca por nombre, cédula/RUC, teléfono o correo. Puedes seleccionar varios.",
    )

    class Meta:
        model = NotificationMessage
        fields = [
            "template",
            "title",
            "body",
            "message_type",
            "priority",
            "branch",
            "recipient_users",
            "recipient_customers",
            "related_customer",
            "related_vehicle",
            "related_sale",
            "related_document",
        ]
        labels = {
            "template": "Plantilla opcional",
            "title": "Título",
            "body": "Mensaje",
            "message_type": "Tipo",
            "priority": "Prioridad",
            "branch": "Sucursal relacionada",
            "related_customer": "Cliente relacionado",
            "related_vehicle": "Vehículo relacionado",
            "related_sale": "Venta / cotización relacionada",
            "related_document": "Documento relacionado",
        }
        widgets = {"body": forms.Textarea(attrs={"rows": 7, "placeholder": "Escribe un mensaje claro, breve y accionable."})}

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["template"].queryset = NotificationTemplate.objects.filter(is_deleted=False, is_active=True).order_by("template_type", "name")
        permission_codes = ("notifications.send",)
        branches = accessible_branches_queryset(user, permission_codes=permission_codes)
        self.fields["branch"].queryset = branches
        self.fields["recipient_users"].queryset = accessible_users_queryset(user, permission_codes=permission_codes)
        customers = scope_queryset_to_user_branches(Customer.objects.filter(is_deleted=False), user=user, permission_codes=permission_codes, branch_lookup="assigned_branch").order_by("business_name", "first_name", "last_name")
        self.fields["recipient_customers"].queryset = customers
        self.fields["related_customer"].queryset = customers
        self.fields["related_vehicle"].queryset = scope_queryset_to_user_branches(Vehicle.objects.filter(is_deleted=False).select_related("brand", "model", "model__brand"), user=user, permission_codes=permission_codes).order_by("brand__name", "model__name", "-year")
        self.fields["related_sale"].queryset = scope_queryset_to_user_branches(SaleRecord.objects.filter(is_deleted=False).select_related("customer"), user=user, permission_codes=permission_codes).order_by("-created_at")
        self.fields["related_document"].queryset = scope_queryset_to_user_branches(PrivateDocument.objects.filter(is_deleted=False), user=user, permission_codes=permission_codes).order_by("-created_at")
        self.fields["template"].required = False
        self.fields["branch"].required = user is not None and accessible_branch_ids(user, permission_codes=permission_codes) is not None
        self.fields["related_customer"].required = False
        self.fields["related_vehicle"].required = False
        self.fields["related_sale"].required = False
        self.fields["related_document"].required = False
        self.fields["template"].empty_label = "Sin plantilla"
        self.fields["branch"].empty_label = "Sin sucursal específica"
        self.fields["related_customer"].empty_label = "Sin cliente relacionado"
        self.fields["related_vehicle"].empty_label = "Sin vehículo relacionado"
        self.fields["related_sale"].empty_label = "Sin venta relacionada"
        self.fields["related_document"].empty_label = "Sin documento relacionado"
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        search_placeholders = {
            "template": "Buscar plantilla...",
            "branch": "Buscar sucursal...",
            "recipient_users": "Buscar usuarios por nombre, usuario o correo...",
            "recipient_customers": "Buscar clientes por nombre, cédula/RUC o correo...",
            "related_customer": "Buscar cliente relacionado...",
            "related_vehicle": "Buscar vehículo por marca, modelo, código interno, VIN real o placa...",
            "related_sale": "Buscar operación por número o cliente...",
            "related_document": "Buscar documento...",
        }
        for name, placeholder in search_placeholders.items():
            _searchable(self.fields[name].widget, placeholder)

    def clean(self):
        cleaned = super().clean()
        users = cleaned.get("recipient_users")
        customers = cleaned.get("recipient_customers")
        if not users and not customers:
            raise forms.ValidationError("Selecciona al menos un destinatario interno o cliente.")
        branch = cleaned.get("branch")
        if branch:
            for field_name, branch_attr in {"related_customer": "assigned_branch_id", "related_vehicle": "branch_id", "related_sale": "branch_id", "related_document": "branch_id"}.items():
                obj = cleaned.get(field_name)
                if obj and getattr(obj, branch_attr, None) not in {None, branch.pk}:
                    self.add_error(field_name, "El registro relacionado debe pertenecer a la sucursal seleccionada.")
            if customers and customers.exclude(assigned_branch_id=branch.pk).exists():
                self.add_error("recipient_customers", "Todos los clientes deben pertenecer a la sucursal seleccionada.")
        return cleaned


class NotificationTemplateSearchForm(forms.Form):
    q = forms.CharField(required=False, label="Buscar", widget=forms.TextInput(attrs={"placeholder": "Nombre, asunto o contenido..."}))
    template_type = forms.ChoiceField(required=False, label="Tipo")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["template_type"].choices = [("", "Todos los tipos")] + list(NotificationTemplate.TemplateType.choices)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class NotificationTemplateForm(forms.ModelForm):
    class Meta:
        model = NotificationTemplate
        fields = ["name", "template_type", "subject", "body", "is_active"]
        labels = {"name": "Nombre interno", "template_type": "Tipo", "subject": "Título sugerido", "body": "Mensaje base", "is_active": "Plantilla activa"}
        widgets = {"body": forms.Textarea(attrs={"rows": 8, "placeholder": "Texto que podrá reutilizar el equipo comercial o administrativo."})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class CampaignForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ["name", "branch", "consent_purpose", "segment_type", "inactivity_days", "brand", "vehicle_model", "customer_created_from", "customer_created_to"]
        widgets = {
            "customer_created_from": forms.DateInput(attrs={"type": "date"}),
            "customer_created_to": forms.DateInput(attrs={"type": "date"}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.fields["branch"].queryset = accessible_branches_queryset(user, permission_codes=("campaigns.manage",))
        self.fields["brand"].queryset = VehicleBrand.objects.filter(is_active=True).order_by("name")
        self.fields["vehicle_model"].queryset = VehicleModel.objects.filter(is_active=True).select_related("brand").order_by("brand__name", "name")
        self.fields["brand"].required = False
        self.fields["vehicle_model"].required = False
        self.fields["customer_created_from"].required = False
        self.fields["customer_created_to"].required = False
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        segment_type = cleaned.get("segment_type")
        if segment_type == Campaign.SegmentType.BRAND and not cleaned.get("brand"):
            self.add_error("brand", "Selecciona la marca del segmento.")
        if segment_type == Campaign.SegmentType.MODEL and not cleaned.get("vehicle_model"):
            self.add_error("vehicle_model", "Selecciona el modelo del segmento.")
        if segment_type == Campaign.SegmentType.CREATED_RANGE:
            date_from = cleaned.get("customer_created_from")
            date_to = cleaned.get("customer_created_to")
            if not date_from or not date_to:
                raise forms.ValidationError("Define las dos fechas del rango de alta de clientes.")
            if date_from > date_to:
                self.add_error("customer_created_to", "La fecha final debe ser igual o posterior a la inicial.")
        return cleaned


class CampaignMessageForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ["template", "subject", "body", "channel"]
        widgets = {"body": forms.Textarea(attrs={"rows": 8})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["template"].queryset = NotificationTemplate.objects.filter(is_deleted=False, is_active=True).order_by("name")
        self.fields["template"].required = False
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        import re

        allowed = {"customer_name", "branch_name", "campaign_name"}
        variables = set(re.findall(r"{([a-zA-Z_][a-zA-Z0-9_]*)}", f"{cleaned.get('subject', '')} {cleaned.get('body', '')}"))
        unsupported = variables - allowed
        if unsupported:
            raise forms.ValidationError(f"Variables no permitidas: {', '.join(sorted(unsupported))}.")
        if "{" in cleaned.get("body", "") and not variables:
            raise forms.ValidationError("La plantilla contiene una variable con formato no permitido.")
        return cleaned
