"""ES: Este módulo define formularios y validación de entrada en backend para el dominio de importaciones.

EN: This module defines forms and server-side input validation for the imports domain.

Contexto existente / Existing context:
Server-side forms and input validation for the imports domain.
"""

from django import forms

from apps.accounts.scopes import accessible_branches_queryset

from apps.branches.models import Branch
from apps.imports.models import ImportBatch


class ImportBatchCreateForm(forms.ModelForm):
    class Meta:
        model = ImportBatch
        fields = ["import_type", "original_file", "default_branch", "require_vehicle_branch", "notes"]
        widgets = {
            "import_type": forms.Select(attrs={"class": "form-control"}),
            "original_file": forms.ClearableFileInput(attrs={"class": "form-control", "accept": ".csv,.xlsx"}),
            "default_branch": forms.Select(attrs={"class": "form-control"}),
            "require_vehicle_branch": forms.CheckboxInput(attrs={"class": "form-check-input"}),
            "notes": forms.Textarea(attrs={"class": "form-control", "rows": 3, "placeholder": "Observaciones internas opcionales"}),
        }
        labels = {
            "import_type": "Tipo de importación",
            "original_file": "Archivo CSV o Excel .xlsx",
            "default_branch": "Sucursal por defecto",
            "require_vehicle_branch": "Exigir sucursal para vehículos",
            "notes": "Notas",
        }
        help_texts = {
            "original_file": "Sube un archivo con encabezados claros. Puedes descargar plantillas desde este módulo.",
            "default_branch": "Se usará cuando la fila no traiga sucursal_codigo o sucursal. Útil para cargar vehículos o stock de una misma concesionaria.",
            "require_vehicle_branch": "Si está activo, cada vehículo debe tener sucursal en la fila o mediante la sucursal por defecto.",
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["default_branch"].required = False
        branches = Branch.objects.filter(is_active=True).order_by("company__commercial_name", "name")
        if user is not None and getattr(user, "is_authenticated", False):
            branches = accessible_branches_queryset(user, permission_codes=("imports.manage",), active_only=True)
        self.fields["default_branch"].queryset = branches
        self.fields["default_branch"].empty_label = "Sin sucursal por defecto"

    def clean_original_file(self):
        uploaded = self.cleaned_data["original_file"]
        name = uploaded.name.lower()
        if not (name.endswith(".csv") or name.endswith(".xlsx")):
            raise forms.ValidationError("Para importaciones masivas solo se aceptan archivos .csv o .xlsx.")
        return uploaded

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("import_type") != ImportBatch.ImportType.VEHICLES:
            cleaned["require_vehicle_branch"] = False
        return cleaned


class ImportFilterForm(forms.Form):
    import_type = forms.ChoiceField(required=False, choices=[("", "Todos los tipos")] + list(ImportBatch.ImportType.choices), widget=forms.Select(attrs={"class": "form-control"}))
    status = forms.ChoiceField(required=False, choices=[("", "Todos los estados")] + list(ImportBatch.Status.choices), widget=forms.Select(attrs={"class": "form-control"}))
    q = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "Buscar archivo, usuario o hash"}))
