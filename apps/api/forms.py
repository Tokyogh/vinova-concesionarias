"""ES: Este módulo define formularios y validación de entrada en backend para el dominio de API e integraciones.

EN: This module defines forms and server-side input validation for the api domain.

Contexto existente / Existing context:
Server-side forms and input validation for the api domain.
"""

from django import forms

from apps.accounts.scopes import users_in_branches_queryset
from apps.api.models import APIClient, WebhookEndpoint
from apps.api.selectors import integration_branch_ids
from apps.api.validators import validate_webhook_url


class APIClientForm(forms.ModelForm):
    class Meta:
        model = APIClient
        fields = [
            "name",
            "description",
            "service_user",
            "branch",
            "scopes",
            "expires_at",
            "allowed_ip_networks",
            "rate_limit",
        ]
        widgets = {
            "description": forms.Textarea(attrs={"rows": 3}),
            "scopes": forms.SelectMultiple(attrs={"size": 12}),
            "expires_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "allowed_ip_networks": forms.Textarea(attrs={"rows": 3, "placeholder": "203.0.113.10/32"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        service_users = self.fields["service_user"].queryset.filter(is_active=True)
        branch_ids = integration_branch_ids(user, ("integrations.manage",)) if user else None
        if branch_ids is not None:
            self.fields["branch"].queryset = self.fields["branch"].queryset.filter(pk__in=branch_ids)
            service_users = service_users.filter(
                pk__in=users_in_branches_queryset(branch_ids).values("pk")
            )
            self.fields["branch"].required = True
        self.fields["service_user"].queryset = service_users.order_by("email")
        self.fields["scopes"].queryset = self.fields["scopes"].queryset.filter(is_active=True).order_by("code")
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        branch_ids = integration_branch_ids(self.user, ("integrations.manage",)) if self.user else None
        branch = cleaned.get("branch")
        service_user = cleaned.get("service_user")
        if branch_ids is not None:
            if not branch or branch.pk not in branch_ids:
                self.add_error("branch", "La sucursal está fuera de tu alcance de integraciones.")
            if service_user and branch and not users_in_branches_queryset((branch.pk,)).filter(pk=service_user.pk).exists():
                self.add_error("service_user", "Selecciona un usuario de servicio de la misma sucursal.")
        return cleaned


class WebhookEndpointForm(forms.ModelForm):
    """ES: Agrupa el componente «webhook endpoint form» del dominio de API e integraciones y sus reglas relacionadas. Además, rechaza estados o entradas inválidas.

    EN: Groups the «webhook endpoint form» component and its related rules in the api domain. It also rejects invalid input or state.
    """

    url = forms.URLField(label="URL", assume_scheme="https")
    event_types_text = forms.CharField(
        label="Eventos",
        help_text="Uno por línea o separados por coma. Ej.: lead.created, sale.updated, invoice.updated o *.",
        widget=forms.Textarea(attrs={"rows": 5}),
    )

    class Meta:
        model = WebhookEndpoint
        fields = ["name", "url", "branch", "timeout_seconds", "max_retries", "is_active"]

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        branch_ids = integration_branch_ids(user, ("integrations.manage",)) if user else None
        if branch_ids is not None:
            self.fields["branch"].queryset = self.fields["branch"].queryset.filter(pk__in=branch_ids)
            self.fields["branch"].required = True
        if self.instance and self.instance.pk:
            self.fields["event_types_text"].initial = "\n".join(self.instance.event_types)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        branch_ids = integration_branch_ids(self.user, ("integrations.manage",)) if self.user else None
        branch = cleaned.get("branch")
        if branch_ids is not None and (not branch or branch.pk not in branch_ids):
            self.add_error("branch", "La sucursal está fuera de tu alcance de integraciones.")
        return cleaned

    def clean_url(self):
        value = self.cleaned_data["url"]
        validate_webhook_url(value)
        return value

    def clean_event_types_text(self):
        raw = self.cleaned_data["event_types_text"].replace(",", "\n")
        values = sorted({item.strip() for item in raw.splitlines() if item.strip()})
        if not values:
            raise forms.ValidationError("Registra al menos un evento.")
        return values

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.event_types = self.cleaned_data["event_types_text"]
        if commit:
            instance.save()
        return instance
