"""ES: Este módulo define formularios y validación de entrada en backend para el dominio de clientes.

EN: This module defines forms and server-side input validation for the customers domain.

Contexto existente / Existing context:
Server-side forms and input validation for the customers domain.
"""

from __future__ import annotations

from django import forms
from django.core.exceptions import ValidationError as DjangoValidationError

from apps.accounts.scopes import accessible_branch_ids
from apps.branches.models import Branch
from apps.common.form_widgets import configure_accessible_filter_fields, make_searchable_select
from apps.common.validators import (
    validate_human_name,
    validate_no_unsafe_control_characters,
    validate_phone_number,
)
from apps.customers.identification import (
    find_exact_duplicate,
    find_fuzzy_candidates,
    normalize_for_storage,
    validate_identification_value,
)
from apps.customers.models import Customer, CustomerNote, CustomerVehicleInterest
from apps.customers.selectors import (
    accessible_customer_advisors_queryset,
    accessible_customer_branches_queryset,
    accessible_customer_vehicles_queryset,
)


CUSTOMER_MANAGE_PERMISSION_CODES = ("customers.manage",)


class CustomerSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Buscar",
        widget=forms.TextInput(attrs={"placeholder": "Nombre, cédula/RUC, correo, teléfono, ciudad..."}),
    )
    identification = forms.CharField(
        required=False,
        label="Cédula / RUC",
        widget=forms.TextInput(attrs={"placeholder": "Cédula o RUC exacto", "inputmode": "numeric"}),
    )
    first_name = forms.CharField(required=False, label="Nombres")
    last_name = forms.CharField(required=False, label="Apellidos")
    email = forms.CharField(required=False, label="Correo")
    phone = forms.CharField(required=False, label="Teléfono", widget=forms.TextInput(attrs={"inputmode": "tel"}))
    plate = forms.CharField(required=False, label="Placa", widget=forms.TextInput(attrs={"placeholder": "Placa del vehículo"}))
    vin = forms.CharField(required=False, label="VIN", widget=forms.TextInput(attrs={"placeholder": "Chasis / VIN"}))
    status = forms.ChoiceField(required=False, label="Estado")
    customer_type = forms.ChoiceField(required=False, label="Tipo")
    branch = forms.ModelChoiceField(required=False, label="Sucursal", queryset=Branch.objects.none())
    sort = forms.ChoiceField(required=False, label="Orden", choices=[
        ("", "Más recientes"), ("name_asc", "Nombre A–Z"),
        ("name_desc", "Nombre Z–A"), ("oldest", "Más antiguos"),
    ])

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = [("", "Todos los estados")] + list(Customer.Status.choices)
        self.fields["customer_type"].choices = [("", "Todos los tipos")] + list(Customer.CustomerType.choices)
        self.fields["branch"].queryset = accessible_customer_branches_queryset(user)
        self.fields["branch"].empty_label = "Todas las sucursales"
        configure_accessible_filter_fields(self.fields)


class CustomerForm(forms.ModelForm):
    """ES: Agrupa el componente «customer form» del dominio de clientes y sus reglas relacionadas. Además, rechaza estados o entradas inválidas.

    EN: Groups the «customer form» component and its related rules in the customers domain. It also rejects invalid input or state.
    """

    class Meta:
        model = Customer
        fields = [
            "customer_type",
            "identification_type",
            "identification_number",
            "first_name",
            "last_name",
            "business_name",
            "email",
            "phone",
            "whatsapp",
            "preferred_contact_method",
            "address",
            "city",
            "province",
            "source",
            "status",
            "assigned_branch",
            "assigned_advisor",
            "internal_notes",
        ]
        labels = {
            "customer_type": "Tipo de cliente",
            "identification_type": "Tipo de identificación",
            "identification_number": "Cédula / RUC / identificación",
            "first_name": "Nombres",
            "last_name": "Apellidos",
            "business_name": "Razón social / empresa",
            "email": "Correo",
            "phone": "Teléfono",
            "whatsapp": "WhatsApp",
            "preferred_contact_method": "Canal preferido",
            "address": "Dirección",
            "city": "Ciudad",
            "province": "Provincia",
            "source": "Origen del cliente",
            "status": "Estado",
            "assigned_branch": "Sucursal asignada",
            "assigned_advisor": "Asesor asignado",
            "internal_notes": "Observaciones internas",
        }
        widgets = {"internal_notes": forms.Textarea(attrs={"rows": 4}), "address": forms.TextInput(), "source": forms.TextInput()}

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fuzzy_candidates = []
        for name in ("first_name", "last_name", "city", "province"):
            self.fields[name].validators.append(validate_human_name)
        for name in ("phone", "whatsapp"):
            self.fields[name].validators.append(validate_phone_number)
            self.fields[name].widget.attrs.setdefault("inputmode", "tel")
        for name in ("business_name", "address", "source", "internal_notes"):
            self.fields[name].validators.append(validate_no_unsafe_control_characters)
        self.fields["assigned_branch"].queryset = accessible_customer_branches_queryset(
            user, permission_codes=CUSTOMER_MANAGE_PERMISSION_CODES
        )
        self.fields["assigned_advisor"].queryset = accessible_customer_advisors_queryset(
            user, permission_codes=CUSTOMER_MANAGE_PERMISSION_CODES
        )
        if accessible_branch_ids(user, permission_codes=CUSTOMER_MANAGE_PERMISSION_CODES) is not None:
            self.fields["assigned_branch"].required = True
        self.fields["assigned_branch"].empty_label = "Sin sucursal asignada"
        self.fields["assigned_advisor"].empty_label = "Sin asesor asignado"
        make_searchable_select(self.fields["assigned_branch"], "Buscar sucursal...")
        make_searchable_select(self.fields["assigned_advisor"], "Buscar asesor por nombre o correo...")
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        """ES: Valida y normaliza «clean» antes de permitir efectos en clientes. Además, rechaza estados o entradas inválidas.

        EN: Validates and normalizes «clean» before allowing effects in customers. It also rejects invalid input or state.
        """

        cleaned = super().clean()
        customer_type = cleaned.get("customer_type")
        first_name = (cleaned.get("first_name") or "").strip()
        last_name = (cleaned.get("last_name") or "").strip()
        business_name = (cleaned.get("business_name") or "").strip()
        identification_number = (cleaned.get("identification_number") or "").strip()
        identification_type = cleaned.get("identification_type") or ""

        if customer_type == Customer.CustomerType.COMPANY and not business_name:
            self.add_error("business_name", "La razón social es obligatoria para clientes empresa.")
        if customer_type == Customer.CustomerType.NATURAL and not (first_name or last_name) and not identification_number:
            self.add_error("first_name", "Registra al menos nombre, apellido o identificación para el cliente.")
        if identification_number:
            normalized = normalize_for_storage(identification_type, identification_number)
            try:
                validate_identification_value(identification_type, normalized)
            except DjangoValidationError as exc:
                self.add_error("identification_number", exc.message_dict.get("identification_number", "Identificación inválida."))
            else:
                cleaned["identification_number"] = normalized
                duplicate = find_exact_duplicate(normalized, exclude_pk=self.instance.pk)
                if duplicate is not None:
                    self.add_error(
                        "identification_number",
                        f"Ya existe un cliente con esta identificación: {duplicate.display_name}.",
                    )
                self.fuzzy_candidates = [
                    candidate
                    for candidate, _ratio in find_fuzzy_candidates(normalized, exclude_pk=self.instance.pk)
                ]
        else:
            self.fuzzy_candidates = []
        return cleaned


class CustomerNoteForm(forms.ModelForm):
    class Meta:
        model = CustomerNote
        fields = ["note_type", "title", "body", "is_important"]
        labels = {"note_type": "Tipo", "title": "Título", "body": "Nota", "is_important": "Marcar como importante"}
        widgets = {"body": forms.Textarea(attrs={"rows": 4, "placeholder": "Detalle de llamada, visita, seguimiento o acuerdo comercial."})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class CustomerVehicleInterestForm(forms.ModelForm):
    class Meta:
        model = CustomerVehicleInterest
        fields = ["vehicle", "brand", "model_name", "year_from", "year_to", "budget_min", "budget_max", "status", "notes"]
        labels = {
            "vehicle": "Vehículo específico",
            "brand": "Marca buscada",
            "model_name": "Modelo buscado",
            "year_from": "Año desde",
            "year_to": "Año hasta",
            "budget_min": "Presupuesto mínimo",
            "budget_max": "Presupuesto máximo",
            "status": "Estado del interés",
            "notes": "Notas del interés",
        }
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["vehicle"].queryset = accessible_customer_vehicles_queryset(
            user, permission_codes=CUSTOMER_MANAGE_PERMISSION_CODES
        )
        self.fields["vehicle"].empty_label = "Sin vehículo específico"
        make_searchable_select(self.fields["vehicle"], "Buscar vehículo por marca, modelo, VIN o placa...")
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class CustomerAccountLinkForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = ["account"]
        labels = {"account": "Cuenta de acceso"}
        help_texts = {"account": "El usuario que representará a este cliente en el portal y garaje digital."}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["account"].queryset = self.fields["account"].queryset.filter(is_active=True).order_by("username")
        self.fields["account"].empty_label = "Sin cuenta vinculada"
        make_searchable_select(self.fields["account"], "Buscar usuario por nombre o correo...")
        self.fields["account"].widget.attrs.setdefault("class", "form-control")
