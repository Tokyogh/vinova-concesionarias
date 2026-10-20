"""ES: Este módulo define formularios y validación de entrada en backend para el dominio de continuidad.

EN: This module defines forms and server-side input validation for the continuity domain.

Contexto existente / Existing context:
Server-side forms and input validation for the continuity domain.
"""

from django import forms

from apps.continuity.models import BackupPolicy, BackupRecord, RestoreDrill


class BackupCreateForm(forms.Form):
    backup_type = forms.ChoiceField(label="Tipo de backup", choices=BackupRecord.BackupType.choices, initial=BackupRecord.BackupType.FULL)
    notes = forms.CharField(required=False, label="Notas", widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class BackupPolicyForm(forms.ModelForm):
    class Meta:
        model = BackupPolicy
        fields = [
            "name", "is_active", "frequency", "retention_days", "include_database", "include_media",
            "include_private", "external_copy_required", "destination_hint", "next_review_at", "notes",
        ]
        widgets = {"next_review_at": forms.DateInput(attrs={"type": "date"}), "notes": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class RestoreDrillForm(forms.ModelForm):
    class Meta:
        model = RestoreDrill
        fields = ["backup", "environment", "planned_at"]
        widgets = {"planned_at": forms.DateTimeInput(attrs={"type": "datetime-local"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["backup"].queryset = BackupRecord.objects.filter(status__in=[BackupRecord.Status.COMPLETED, BackupRecord.Status.VERIFIED]).order_by("-created_at")
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class RestoreDrillResultForm(forms.ModelForm):
    class Meta:
        model = RestoreDrill
        fields = ["status", "result_summary"]
        widgets = {"result_summary": forms.Textarea(attrs={"rows": 5})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = [
            (RestoreDrill.Status.PASSED, "Aprobado"),
            (RestoreDrill.Status.FAILED, "Fallido"),
            (RestoreDrill.Status.CANCELLED, "Cancelado"),
        ]
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
