"""ES: Este módulo define formularios y validación de entrada en backend para el dominio de documentos.

EN: This module defines forms and server-side input validation for the documents domain.

Contexto existente / Existing context:
Server-side forms and input validation for the documents domain.
"""

from __future__ import annotations

from django import forms

from apps.branches.models import Branch
from apps.documents.models import DocumentCategory, PrivateDocument, ReusableAsset
from apps.documents.selectors import allowed_document_branch_ids, has_global_document_scope
from apps.common.form_widgets import make_searchable_select
from apps.vehicles.models import VehicleModel


class DocumentSearchForm(forms.Form):
    q = forms.CharField(required=False, label="Buscar", widget=forms.TextInput(attrs={"placeholder": "Documento, cliente, VIN, venta, archivo..."}))
    document_type = forms.ChoiceField(required=False, label="Tipo")
    status = forms.ChoiceField(required=False, label="Estado")
    branch = forms.ModelChoiceField(queryset=Branch.objects.filter(is_active=True).order_by("name"), required=False, label="Sucursal")
    sort = forms.ChoiceField(required=False, label="Orden", choices=[
        ("", "Más recientes"), ("oldest", "Más antiguos"),
        ("title_asc", "Título A–Z"), ("expires_asc", "Próximos a vencer"),
    ])

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None and getattr(user, "is_authenticated", False) and not has_global_document_scope(user):
            self.fields["branch"].queryset = self.fields["branch"].queryset.filter(pk__in=allowed_document_branch_ids(user))
        self.fields["document_type"].choices = [("", "Todos los tipos")] + list(PrivateDocument.DocumentType.choices)
        self.fields["status"].choices = [("", "Todos los estados")] + list(PrivateDocument.Status.choices)
        self.fields["branch"].empty_label = "Todas las sucursales"
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        make_searchable_select(self.fields["branch"], "Buscar sucursal...")


class AssetSearchForm(forms.Form):
    q = forms.CharField(required=False, label="Buscar", widget=forms.TextInput(attrs={"placeholder": "Título, archivo, hash, descripción..."}))
    asset_type = forms.ChoiceField(required=False, label="Tipo")
    visibility = forms.ChoiceField(required=False, label="Visibilidad")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["asset_type"].choices = [("", "Todos los tipos")] + list(ReusableAsset.AssetType.choices)
        self.fields["visibility"].choices = [("", "Toda visibilidad")] + list(ReusableAsset.Visibility.choices)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class ReusableAssetForm(forms.ModelForm):
    class Meta:
        model = ReusableAsset
        fields = [
            "title", "asset_type", "file", "visibility", "description", "alt_text",
            "branch", "vehicle_model", "vehicle_year", "is_active",
        ]
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        branch_qs = Branch.objects.filter(is_active=True).order_by("company__commercial_name", "name")
        if user is not None and getattr(user, "is_authenticated", False) and not has_global_document_scope(user):
            branch_qs = branch_qs.filter(pk__in=allowed_document_branch_ids(user))
            self.fields["branch"].required = True
            self.fields["branch"].help_text = "Tu rol solo puede administrar recursos de sus sucursales asignadas."
            if not self.instance.pk and branch_qs.count() == 1:
                self.fields["branch"].initial = branch_qs.first()
        self.fields["branch"].queryset = branch_qs
        self.fields["vehicle_model"].queryset = VehicleModel.objects.filter(is_active=True).select_related("brand")
        self.fields["vehicle_model"].required = False
        self.fields["vehicle_model"].empty_label = "Sin modelo específico"
        self.fields["branch"].empty_label = "Sin sucursal específica"
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        make_searchable_select(self.fields["branch"], "Buscar sucursal...")
        make_searchable_select(self.fields["vehicle_model"], "Buscar marca o modelo...")

    def clean(self):
        cleaned = super().clean()
        vehicle_model = cleaned.get("vehicle_model")
        if cleaned.get("asset_type") == ReusableAsset.AssetType.MANUAL and vehicle_model is None:
            self.add_error("vehicle_model", "Selecciona el modelo al que corresponde el manual.")
        if cleaned.get("vehicle_year") is not None and vehicle_model is None:
            self.add_error("vehicle_year", "Selecciona un modelo antes de indicar el año.")
        return cleaned


class PrivateDocumentForm(forms.ModelForm):
    class Meta:
        model = PrivateDocument
        fields = [
            "title", "document_type", "category", "file", "status", "branch", "customer", "vehicle", "sale", "expires_at", "is_confidential", "notes",
        ]
        widgets = {
            "expires_at": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].queryset = DocumentCategory.objects.filter(is_active=True).order_by("scope", "name")
        branch_qs = Branch.objects.filter(is_active=True).order_by("company__commercial_name", "name")
        scoped_user = user is not None and getattr(user, "is_authenticated", False) and not has_global_document_scope(user)
        if scoped_user:
            branch_qs = branch_qs.filter(pk__in=allowed_document_branch_ids(user))
        self.fields["branch"].queryset = branch_qs
        for name in ["category", "branch", "customer", "vehicle", "sale"]:
            self.fields[name].required = False
        if scoped_user:
            self.fields["branch"].required = True
            self.fields["branch"].help_text = "Tu rol solo puede administrar documentos de sus sucursales asignadas."
            if not self.instance.pk and branch_qs.count() == 1:
                self.fields["branch"].initial = branch_qs.first()
        self.fields["category"].empty_label = "Sin categoría"
        self.fields["branch"].empty_label = "Sin sucursal específica"
        self.fields["customer"].empty_label = "Sin cliente relacionado"
        self.fields["vehicle"].empty_label = "Sin vehículo relacionado"
        self.fields["sale"].empty_label = "Sin venta relacionada"
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        for field_name, placeholder in {"category":"Buscar categoría...","branch":"Buscar sucursal...","customer":"Buscar cliente...","vehicle":"Buscar vehículo...","sale":"Buscar venta..."}.items():
            make_searchable_select(self.fields[field_name], placeholder)


class DocumentCategoryForm(forms.ModelForm):
    class Meta:
        model = DocumentCategory
        fields = ["name", "scope", "description", "is_active"]
