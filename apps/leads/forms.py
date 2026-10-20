"""ES: Este módulo define formularios y validación de entrada en backend para el dominio de CRM y leads.

EN: This module defines forms and server-side input validation for the leads domain.

Contexto existente / Existing context:
Server-side forms and input validation for the leads domain.
"""

from __future__ import annotations

from decimal import Decimal

from django import forms
from django.utils import timezone

from apps.accounts.models import User
from apps.accounts.scopes import accessible_branch_ids
from apps.branches.models import Branch
from apps.common.form_widgets import make_searchable_select
from apps.common.validators import (
    validate_human_name,
    validate_no_unsafe_control_characters,
    validate_phone_number,
)
from apps.customers.selectors import accessible_customer_queryset
from apps.leads.models import Lead, LeadActivity, TestDrive
from apps.leads.selectors import (
    accessible_lead_advisors_queryset,
    accessible_lead_branches_queryset,
    accessible_lead_vehicles_queryset,
)
from apps.vehicles.models import Vehicle


LEAD_VIEW_PERMISSION_CODES = ("leads.view",)
LEAD_MANAGE_PERMISSION_CODES = ("leads.manage",)
LEAD_ASSIGN_PERMISSION_CODES = ("leads.assign",)
MAX_COMMERCIAL_BUDGET = Decimal("9999999999.99")


class PublicLeadForm(forms.ModelForm):
    """ES: Valida una solicitud comercial pública y su canal de respuesta elegido.

    EN: Validates a public commercial request and its selected response channel.
    """

    website = forms.CharField(required=False, widget=forms.HiddenInput(), label="No completar")
    consent_data_processing = forms.BooleanField(
        required=True,
        label="Autorizo el tratamiento de mis datos para responder esta solicitud comercial.",
    )

    class Meta:
        model = Lead
        fields = [
            "request_type", "full_name", "email", "phone", "whatsapp", "preferred_contact_method",
            "city", "province", "budget_min", "budget_max", "expected_purchase_date", "message",
            "consent_data_processing",
        ]
        labels = {
            "request_type": "¿Qué necesitas?", "full_name": "Nombre completo", "email": "Correo",
            "phone": "Teléfono", "whatsapp": "WhatsApp", "preferred_contact_method": "Canal preferido",
            "city": "Ciudad", "province": "Provincia", "budget_min": "Presupuesto mínimo",
            "budget_max": "Presupuesto máximo", "expected_purchase_date": "Fecha estimada de compra",
            "message": "Mensaje o consulta",
        }
        widgets = {
            "expected_purchase_date": forms.DateInput(attrs={"type": "date"}),
            "message": forms.Textarea(attrs={"rows": 4, "placeholder": "Cuéntanos qué vehículo buscas o qué información necesitas."}),
        }

    def __init__(self, *args, **kwargs):
        self.vehicle = kwargs.pop("vehicle", None)
        super().__init__(*args, **kwargs)
        self.fields["full_name"].validators.append(validate_human_name)
        for name in ("phone", "whatsapp"):
            self.fields[name].validators.append(validate_phone_number)
            self.fields[name].widget.attrs.setdefault("inputmode", "tel")
        for name in ("city", "province"):
            self.fields[name].validators.append(validate_human_name)
        self.fields["message"].validators.append(validate_no_unsafe_control_characters)
        for name in ("budget_min", "budget_max"):
            self.fields[name].min_value = 0
            self.fields[name].max_value = MAX_COMMERCIAL_BUDGET
            self.fields[name].widget.attrs.update({"min": "0", "max": str(MAX_COMMERCIAL_BUDGET), "step": "0.01", "inputmode": "decimal"})
            self.fields[name].help_text = "Valor referencial opcional en USD; usa solo números y hasta dos decimales."
        self.fields["preferred_contact_method"].widget = forms.Select(choices=[("whatsapp", "WhatsApp"), ("phone", "Teléfono"), ("email", "Correo")])
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_website(self):
        if self.cleaned_data.get("website"):
            raise forms.ValidationError("Solicitud no válida.")
        return ""

    def clean(self):
        """ES: Exige un contacto coherente y fechas futuras sin inventar reglas comerciales.

        EN: Requires coherent contact data and future dates without inventing business rules.
        """

        cleaned = super().clean()
        if not (cleaned.get("email") or cleaned.get("phone") or cleaned.get("whatsapp")):
            self.add_error("phone", "Registra al menos teléfono, WhatsApp o correo.")
        preferred = cleaned.get("preferred_contact_method")
        if preferred == "phone" and not cleaned.get("phone"):
            self.add_error("phone", "Registra un teléfono para usarlo como canal preferido.")
        elif preferred == "whatsapp" and not cleaned.get("whatsapp"):
            self.add_error("whatsapp", "Registra un número de WhatsApp para usarlo como canal preferido.")
        elif preferred == "email" and not cleaned.get("email"):
            self.add_error("email", "Registra un correo para usarlo como canal preferido.")
        expected = cleaned.get("expected_purchase_date")
        if expected and expected < timezone.localdate():
            self.add_error("expected_purchase_date", "La fecha estimada no puede estar en el pasado.")
        return cleaned


class LeadSearchForm(forms.Form):
    q = forms.CharField(required=False, label="Buscar", widget=forms.TextInput(attrs={"placeholder": "Código, nombre, correo, teléfono, ciudad o vehículo..."}))
    status = forms.ChoiceField(required=False, label="Estado")
    priority = forms.ChoiceField(required=False, label="Prioridad")
    source = forms.ChoiceField(required=False, label="Origen")
    request_type = forms.ChoiceField(required=False, label="Solicitud")
    branch = forms.ModelChoiceField(required=False, label="Sucursal", queryset=Branch.objects.none())
    advisor = forms.ModelChoiceField(required=False, label="Asesor", queryset=User.objects.none())
    overdue = forms.BooleanField(required=False, label="Solo seguimientos vencidos")
    sort = forms.ChoiceField(required=False, label="Orden", choices=[
        ("", "Prioridad y seguimiento"), ("newest", "Más recientes"),
        ("oldest", "Más antiguos"), ("follow_up", "Próximo seguimiento"),
    ])

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = [("", "Todos los estados")] + list(Lead.Status.choices)
        self.fields["priority"].choices = [("", "Todas las prioridades")] + list(Lead.Priority.choices)
        self.fields["source"].choices = [("", "Todos los orígenes")] + list(Lead.Source.choices)
        self.fields["request_type"].choices = [("", "Todas las solicitudes")] + list(Lead.RequestType.choices)
        self.fields["branch"].queryset = accessible_lead_branches_queryset(
            user, permission_codes=LEAD_VIEW_PERMISSION_CODES
        )
        self.fields["advisor"].queryset = accessible_lead_advisors_queryset(
            user, permission_codes=LEAD_VIEW_PERMISSION_CODES
        )
        self.fields["branch"].empty_label = "Todas las sucursales"
        self.fields["advisor"].empty_label = "Todos los asesores"
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class InternalLeadForm(forms.ModelForm):
    """ES: Agrupa el componente «internal lead form» del dominio de CRM y leads y sus reglas relacionadas.

    EN: Groups the «internal lead form» component and its related rules in the leads domain.
    """

    class Meta:
        model = Lead
        fields = [
            "request_type", "status", "priority", "source", "full_name", "email", "phone", "whatsapp",
            "preferred_contact_method", "city", "province", "customer", "vehicle", "branch", "assigned_advisor",
            "interested_brand", "interested_model", "budget_min", "budget_max", "expected_purchase_date",
            "message", "internal_notes", "next_follow_up_at", "lost_reason",
        ]
        labels = {
            "request_type": "Tipo de solicitud", "status": "Estado", "priority": "Prioridad", "source": "Origen",
            "full_name": "Nombre completo", "email": "Correo", "phone": "Teléfono", "whatsapp": "WhatsApp",
            "preferred_contact_method": "Canal preferido", "city": "Ciudad", "province": "Provincia",
            "customer": "Cliente relacionado", "vehicle": "Vehículo de interés", "branch": "Sucursal",
            "assigned_advisor": "Asesor asignado", "interested_brand": "Marca de interés",
            "interested_model": "Modelo de interés", "budget_min": "Presupuesto mínimo", "budget_max": "Presupuesto máximo",
            "expected_purchase_date": "Compra estimada", "message": "Consulta del cliente", "internal_notes": "Notas internas",
            "next_follow_up_at": "Próximo seguimiento", "lost_reason": "Motivo de pérdida",
        }
        widgets = {
            "expected_purchase_date": forms.DateInput(attrs={"type": "date"}),
            "next_follow_up_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "message": forms.Textarea(attrs={"rows": 3}), "internal_notes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["full_name"].validators.append(validate_human_name)
        for name in ("phone", "whatsapp"):
            self.fields[name].validators.append(validate_phone_number)
            self.fields[name].widget.attrs.setdefault("inputmode", "tel")
        for name in ("city", "province"):
            self.fields[name].validators.append(validate_human_name)
        for name in ("message", "internal_notes", "lost_reason"):
            self.fields[name].validators.append(validate_no_unsafe_control_characters)
        for name in ("budget_min", "budget_max"):
            self.fields[name].min_value = 0
            self.fields[name].max_value = MAX_COMMERCIAL_BUDGET
            self.fields[name].widget.attrs.update({"min": "0", "max": str(MAX_COMMERCIAL_BUDGET), "step": "0.01", "inputmode": "decimal"})
        self.fields["preferred_contact_method"].widget = forms.Select(choices=[("whatsapp", "WhatsApp"), ("phone", "Teléfono"), ("email", "Correo")])
        self.fields["customer"].queryset = accessible_customer_queryset(
            user, permission_codes=LEAD_MANAGE_PERMISSION_CODES
        ).order_by("business_name", "first_name", "last_name")
        self.fields["vehicle"].queryset = accessible_lead_vehicles_queryset(
            user, permission_codes=LEAD_MANAGE_PERMISSION_CODES
        )
        self.fields["branch"].queryset = accessible_lead_branches_queryset(
            user, permission_codes=LEAD_MANAGE_PERMISSION_CODES
        )
        self.fields["assigned_advisor"].queryset = accessible_lead_advisors_queryset(
            user, permission_codes=LEAD_MANAGE_PERMISSION_CODES
        )
        for name in ["customer", "vehicle", "branch", "assigned_advisor"]:
            self.fields[name].required = False
            self.fields[name].empty_label = "Sin asignar"
        make_searchable_select(self.fields["customer"], "Buscar cliente...")
        make_searchable_select(self.fields["vehicle"], "Buscar vehículo por código, marca, modelo o VIN...")
        make_searchable_select(self.fields["branch"], "Buscar sucursal...")
        make_searchable_select(self.fields["assigned_advisor"], "Buscar asesor...")
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

        if accessible_branch_ids(user, permission_codes=LEAD_MANAGE_PERMISSION_CODES) is not None:
            self.fields["branch"].required = True

    def clean(self):
        cleaned = super().clean()
        branch = cleaned.get("branch")
        customer = cleaned.get("customer")
        vehicle = cleaned.get("vehicle")
        if branch and customer and customer.assigned_branch_id not in (None, branch.pk):
            self.add_error("customer", "El cliente pertenece a otra sucursal.")
        if branch and vehicle and vehicle.branch_id not in (None, branch.pk):
            self.add_error("vehicle", "El vehículo pertenece a otra sucursal.")
        return cleaned


class LeadActivityForm(forms.ModelForm):
    class Meta:
        model = LeadActivity
        fields = ["activity_type", "title", "detail", "outcome", "scheduled_for", "completed_at"]
        labels = {"activity_type": "Tipo", "title": "Título", "detail": "Detalle", "outcome": "Resultado", "scheduled_for": "Programado para", "completed_at": "Completado el"}
        widgets = {
            "detail": forms.Textarea(attrs={"rows": 4}),
            "scheduled_for": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "completed_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class LeadStatusForm(forms.Form):
    status = forms.ChoiceField(label="Nuevo estado", choices=Lead.Status.choices)
    note = forms.CharField(required=False, label="Nota del cambio", widget=forms.Textarea(attrs={"rows": 3}))
    lost_reason = forms.CharField(required=False, label="Motivo de pérdida", widget=forms.Textarea(attrs={"rows": 2}))
    next_follow_up_at = forms.DateTimeField(required=False, label="Próximo seguimiento", widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("status") == Lead.Status.LOST and not (cleaned.get("lost_reason") or "").strip():
            self.add_error("lost_reason", "El motivo es obligatorio al marcar un lead como perdido.")
        return cleaned


class LeadAssignmentForm(forms.Form):
    branch = forms.ModelChoiceField(required=False, label="Sucursal", queryset=Branch.objects.none())
    assigned_advisor = forms.ModelChoiceField(required=False, label="Asesor", queryset=User.objects.none())
    note = forms.CharField(required=False, label="Nota", widget=forms.Textarea(attrs={"rows": 2}))

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["branch"].queryset = accessible_lead_branches_queryset(
            user, permission_codes=LEAD_ASSIGN_PERMISSION_CODES
        )
        self.fields["assigned_advisor"].queryset = accessible_lead_advisors_queryset(
            user, permission_codes=LEAD_ASSIGN_PERMISSION_CODES
        )
        if accessible_branch_ids(user, permission_codes=LEAD_ASSIGN_PERMISSION_CODES) is not None:
            self.fields["branch"].required = True
        self.fields["branch"].empty_label = "Sin sucursal"
        self.fields["assigned_advisor"].empty_label = "Sin asesor"
        make_searchable_select(self.fields["branch"], "Buscar sucursal...")
        make_searchable_select(self.fields["assigned_advisor"], "Buscar asesor...")
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class TestDriveForm(forms.ModelForm):
    class Meta:
        model = TestDrive
        fields = ["vehicle", "branch", "advisor", "starts_at", "ends_at", "status", "notes"]
        labels = {"vehicle": "Vehículo", "branch": "Sucursal", "advisor": "Asesor", "starts_at": "Inicio", "ends_at": "Fin", "status": "Estado", "notes": "Notas"}
        widgets = {
            "starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "ends_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }

    def __init__(self, *args, lead=None, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["vehicle"].queryset = accessible_lead_vehicles_queryset(
            user, permission_codes=LEAD_MANAGE_PERMISSION_CODES
        ).exclude(status__in=[Vehicle.Status.SOLD, Vehicle.Status.ARCHIVED])
        self.fields["branch"].queryset = accessible_lead_branches_queryset(
            user, permission_codes=LEAD_MANAGE_PERMISSION_CODES
        )
        self.fields["advisor"].queryset = accessible_lead_advisors_queryset(
            user, permission_codes=LEAD_MANAGE_PERMISSION_CODES
        )
        if lead:
            self.fields["vehicle"].initial = lead.vehicle_id
            self.fields["branch"].initial = lead.branch_id or getattr(lead.vehicle, "branch_id", None)
            self.fields["advisor"].initial = lead.assigned_advisor_id
        make_searchable_select(self.fields["vehicle"], "Buscar vehículo...")
        make_searchable_select(self.fields["branch"], "Buscar sucursal...")
        make_searchable_select(self.fields["advisor"], "Buscar asesor...")
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
