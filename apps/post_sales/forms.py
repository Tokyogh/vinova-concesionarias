"""ES: Este módulo define formularios y validación de entrada en backend para el dominio de postventa.

EN: This module defines forms and server-side input validation for the post sales domain.

Contexto existente / Existing context:
Server-side forms and input validation for the post sales domain.
"""

from django import forms

from apps.accounts.scopes import accessible_branches_queryset, accessible_users_queryset, scope_queryset_to_user_branches
from apps.customers.models import Customer
from apps.post_sales.models import ServiceOrder, ServiceOrderLine
from apps.vehicles.models import Vehicle


class ServiceOrderForm(forms.ModelForm):
    """ES: Agrupa el componente «service order form» del dominio de postventa y sus reglas relacionadas.

    EN: Groups the «service order form» component and its related rules in the post sales domain.
    """

    class Meta:
        model = ServiceOrder
        fields = (
            "number",
            "branch",
            "customer",
            "vehicle",
            "responsible",
            "description",
            "scheduled_at",
            "reception_mileage",
            "diagnosis",
            "next_service_date",
            "next_service_mileage",
            "labor_cost",
            "parts_cost",
            "external_cost",
            "documents",
        )
        widgets = {
            "scheduled_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "next_service_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 4}),
            "diagnosis": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        permissions = ("post_sales.manage",)
        self.fields["branch"].queryset = accessible_branches_queryset(user, permission_codes=permissions)
        self.fields["customer"].queryset = scope_queryset_to_user_branches(
            Customer.objects.filter(is_deleted=False),
            user=user,
            permission_codes=permissions,
            branch_lookup="assigned_branch",
        )
        self.fields["vehicle"].queryset = scope_queryset_to_user_branches(
            Vehicle.objects.filter(is_deleted=False),
            user=user,
            permission_codes=permissions,
        )
        self.fields["responsible"].queryset = accessible_users_queryset(user, permission_codes=permissions)
        document_qs = self.fields["documents"].queryset
        self.fields["documents"].queryset = scope_queryset_to_user_branches(
            document_qs.filter(is_deleted=False),
            user=user,
            permission_codes=permissions,
        )
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        branch = cleaned.get("branch")
        vehicle = cleaned.get("vehicle")
        customer = cleaned.get("customer")
        if branch and vehicle and vehicle.branch_id != branch.pk:
            self.add_error("vehicle", "El vehículo pertenece a otra sucursal.")
        if branch and customer and customer.assigned_branch_id not in (None, branch.pk):
            self.add_error("customer", "El cliente pertenece a otra sucursal.")
        return cleaned


class ServiceOrderSearchForm(forms.Form):
    q = forms.CharField(required=False, max_length=100)
    status = forms.ChoiceField(required=False, choices=[("", "Todos los estados")] + list(ServiceOrder.Status.choices))


class ServiceOrderStatusForm(forms.Form):
    status = forms.ChoiceField(choices=ServiceOrder.Status.choices)
    note = forms.CharField(required=False, max_length=220)

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("status") == ServiceOrder.Status.CANCELLED and not cleaned.get("note", "").strip():
            self.add_error("note", "Indica el motivo de cancelación.")
        return cleaned


class ServiceOrderOperationalForm(forms.ModelForm):
    class Meta:
        model = ServiceOrder
        fields = (
            "scheduled_at",
            "reception_mileage",
            "delivery_mileage",
            "diagnosis",
            "next_service_date",
            "next_service_mileage",
        )
        widgets = {
            "scheduled_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "next_service_date": forms.DateInput(attrs={"type": "date"}),
            "diagnosis": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class ServiceOrderLineForm(forms.ModelForm):
    class Meta:
        model = ServiceOrderLine
        fields = ("line_type", "description", "responsible", "quantity", "unit_cost")

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["responsible"].queryset = accessible_users_queryset(
            user,
            permission_codes=("post_sales.manage",),
        )
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
