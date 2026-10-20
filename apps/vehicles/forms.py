"""ES: Este módulo define formularios y validación de entrada en backend para el dominio de vehículos.

EN: This module defines forms and server-side input validation for the vehicles domain.

Contexto existente / Existing context:
Server-side forms and input validation for the vehicles domain.
"""

from __future__ import annotations

from pathlib import Path

from django import forms

from apps.accounts.scopes import accessible_branch_ids, accessible_branches_queryset
from apps.branches.models import Branch
from apps.common.validators import (
    DOCUMENT_EXTENSIONS,
    IMAGE_EXTENSIONS,
    MODEL_3D_EXTENSIONS,
    VIDEO_EXTENSIONS,
    validate_upload_extension,
    validate_upload_size,
    validate_nonnegative_decimal,
    validate_vehicle_identifier,
    validate_vehicle_plate,
    validate_vehicle_year,
    validate_no_unsafe_control_characters,
)
from apps.vehicles.models import (
    Vehicle,
    VehicleBrand,
    VehicleCommercialHighlight,
    VehicleMedia,
    VehicleModel,
    VehiclePartSpecification,
)
from apps.common.form_widgets import make_searchable_select


class VehicleSearchForm(forms.Form):
    q = forms.CharField(required=False, label="Buscar", widget=forms.TextInput(attrs={"placeholder": "Marca, modelo, código interno, VIN, placa..."}))
    vin = forms.CharField(required=False, label="VIN", widget=forms.TextInput(attrs={"placeholder": "Chasis / VIN"}))
    plate = forms.CharField(required=False, label="Placa", widget=forms.TextInput(attrs={"placeholder": "Placa"}))
    internal_code = forms.CharField(required=False, label="Código interno")
    brand = forms.ModelChoiceField(required=False, label="Marca", queryset=VehicleBrand.objects.filter(is_active=True))
    model = forms.ModelChoiceField(required=False, label="Modelo", queryset=VehicleModel.objects.filter(is_active=True))
    status = forms.ChoiceField(required=False, label="Estado")
    branch = forms.ModelChoiceField(required=False, label="Sucursal", queryset=Branch.objects.none())
    sort = forms.ChoiceField(required=False, label="Orden", choices=[
        ("", "Destacados y recientes"), ("newest", "Más recientes"),
        ("price_asc", "Precio: menor a mayor"), ("price_desc", "Precio: mayor a menor"),
        ("year_desc", "Año: más nuevo"),
    ])

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["vin"].validators.append(validate_vehicle_identifier)
        self.fields["plate"].validators.append(validate_vehicle_plate)
        self.fields["plate"].widget.attrs.setdefault("placeholder", "ABC-1234")
        self.fields["status"].choices = [("", "Todos los estados")] + list(Vehicle.Status.choices)
        self.fields["branch"].queryset = accessible_branches_queryset(
            user,
            permission_codes=("vehicles.view", "vehicles.manage", "vehicles.publish"),
        )
        self.fields["branch"].empty_label = "Todas las sucursales"
        self.fields["brand"].empty_label = "Todas las marcas"
        self.fields["model"].empty_label = "Todos los modelos"
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        make_searchable_select(self.fields["branch"], "Buscar sucursal...")
        make_searchable_select(self.fields["brand"], "Buscar marca...")
        make_searchable_select(self.fields["model"], "Buscar modelo...")


class VehicleBrandForm(forms.ModelForm):
    class Meta:
        model = VehicleBrand
        fields = ["name", "logo", "is_active"]
        labels = {"name": "Marca", "logo": "Logo", "is_active": "Activa"}


class VehicleModelForm(forms.ModelForm):
    class Meta:
        model = VehicleModel
        fields = ["brand", "name", "segment", "is_active"]
        labels = {"brand": "Marca", "name": "Modelo", "segment": "Segmento / gama", "is_active": "Activo"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["brand"].queryset = VehicleBrand.objects.filter(is_active=True).order_by("name")
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        make_searchable_select(self.fields["brand"], "Buscar marca...")


class VehicleForm(forms.ModelForm):
    """ES: Agrupa el componente «vehicle form» del dominio de vehículos y sus reglas relacionadas.

    EN: Groups the «vehicle form» component and its related rules in the vehicles domain.
    """

    change_reason = forms.CharField(
        label="Justificación del cambio sensible",
        required=False,
        max_length=220,
        widget=forms.Textarea(attrs={"rows": 2}),
        help_text="Obligatoria al cambiar VIN, marca, modelo o año de un vehículo existente.",
    )

    class Meta:
        model = Vehicle
        fields = [
            "brand",
            "model",
            "branch",
            "year",
            "version",
            "vin",
            "plate",
            "color",
            "mileage",
            "price",
            "status",
            "short_description",
            "description",
            "is_featured",
            "change_reason",
        ]
        labels = {
            "brand": "Marca",
            "model": "Modelo",
            "branch": "Sucursal / concesionaria",
            "year": "Año",
            "version": "Versión",
            "vin": "VIN real / número de chasis",
            "plate": "Placa",
            "color": "Color",
            "mileage": "Kilometraje",
            "price": "Precio",
            "status": "Estado",
            "short_description": "Descripción corta comercial",
            "description": "Descripción completa",
            "is_featured": "Destacar en portada pública",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "short_description": forms.Textarea(attrs={"rows": 2, "maxlength": 220}),
        }
        help_texts = {
            "vin": "Opcional. Registra el VIN real asignado por el fabricante; Vinova Pro no inventa números de chasis.",
            "branch": "Puede quedar vacío si todavía no se asigna a una sucursal.",
            "status": "Solo Disponible aparece en el catálogo público.",
            "is_featured": "Los destacados aparecen primero en la portada y catálogo público.",
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["year"].validators.append(validate_vehicle_year)
        self.fields["vin"].validators.append(validate_vehicle_identifier)
        self.fields["plate"].validators.append(validate_vehicle_plate)
        self.fields["plate"].widget.attrs.setdefault("placeholder", "ABC-1234")
        self.fields["price"].validators.append(validate_nonnegative_decimal)
        self.fields["price"].widget.attrs.setdefault("min", "0")
        self.fields["mileage"].widget.attrs.setdefault("min", "0")
        for name in ("version", "color", "short_description", "description", "change_reason"):
            self.fields[name].validators.append(validate_no_unsafe_control_characters)
        self.fields["brand"].queryset = VehicleBrand.objects.filter(is_active=True).order_by("name")
        self.fields["model"].queryset = VehicleModel.objects.filter(is_active=True).select_related("brand").order_by("brand__name", "name")
        self.fields["branch"].queryset = accessible_branches_queryset(
            user,
            permission_codes=("vehicles.manage",),
        )
        if accessible_branch_ids(user, permission_codes=("vehicles.manage",)) is not None:
            self.fields["branch"].required = True
            self.fields["branch"].help_text = "Selecciona una sucursal dentro de tu alcance operativo."
        self.fields["branch"].empty_label = "Sin sucursal asignada"
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        make_searchable_select(self.fields["brand"], "Buscar marca...")
        make_searchable_select(self.fields["model"], "Buscar modelo...")
        make_searchable_select(self.fields["branch"], "Buscar sucursal...")
        if not self.instance.pk:
            self.fields.pop("change_reason")

    def clean(self):
        cleaned = super().clean()
        brand = cleaned.get("brand")
        model = cleaned.get("model")
        if brand and model and model.brand_id != brand.id:
            self.add_error("model", "El modelo seleccionado no pertenece a la marca indicada.")
        if self.instance.pk:
            sensitive_changed = any(
                field in self.changed_data for field in ("brand", "model", "year", "vin")
            )
            if sensitive_changed and not (cleaned.get("change_reason") or "").strip():
                self.add_error("change_reason", "Explica por qué se modifica la identidad técnica del vehículo.")
        return cleaned

class VehicleMediaMetadataForm(forms.ModelForm):
    """ES: Edita metadatos de una asociación multimedia existente.

    EN: Edits metadata for an existing media association.
    """

    class Meta:
        model = VehicleMedia
        fields = ["media_type", "title", "alt_text", "order", "is_public"]
        labels = {
            "media_type": "Tipo",
            "title": "Título",
            "alt_text": "Texto alternativo",
            "order": "Orden",
            "is_public": "Visible públicamente",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("title", "alt_text"):
            self.fields[name].validators.append(validate_no_unsafe_control_characters)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class VehicleCommercialHighlightForm(forms.ModelForm):
    """ES: Gestiona destacados comerciales mostrados por las interfaces.

    EN: Manages commercial highlights rendered by user interfaces.
    """

    class Meta:
        model = VehicleCommercialHighlight
        fields = ["title", "value", "icon", "order"]
        labels = {"title": "Título", "value": "Valor", "icon": "Icono", "order": "Orden"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("title", "value", "icon"):
            self.fields[name].validators.append(validate_no_unsafe_control_characters)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")


class VehiclePartSpecificationForm(forms.ModelForm):
    """ES: Gestiona características y especificaciones técnicas estructuradas.

    EN: Manages structured features and technical specifications.
    """

    class Meta:
        model = VehiclePartSpecification
        fields = [
            "part_code", "title", "summary", "description", "image", "specs",
            "hotspot_label", "hotspot_x", "hotspot_y", "hotspot_z", "order",
        ]
        labels = {
            "part_code": "Área",
            "title": "Título",
            "summary": "Resumen",
            "description": "Descripción",
            "image": "Imagen reutilizable",
            "specs": "Especificaciones JSON",
            "hotspot_label": "Etiqueta 3D",
            "hotspot_x": "Posición X",
            "hotspot_y": "Posición Y",
            "hotspot_z": "Posición Z",
            "order": "Orden",
        }
        widgets = {
            "description": forms.Textarea(attrs={"rows": 4}),
            "specs": forms.Textarea(attrs={"rows": 5}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("title", "summary", "description", "hotspot_label"):
            self.fields[name].validators.append(validate_no_unsafe_control_characters)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        self.fields["image"].queryset = self.fields["image"].queryset.filter(resource_type="image")
        make_searchable_select(self.fields["image"], "Buscar imagen reutilizable...")

    def clean_specs(self):
        specs = self.cleaned_data.get("specs") or {}
        if not isinstance(specs, dict):
            raise forms.ValidationError("Las especificaciones deben ser un objeto JSON de clave y valor.")
        if len(specs) > 50:
            raise forms.ValidationError("Registra como máximo 50 especificaciones por sección.")
        return specs


class VehicleMediaUploadForm(forms.Form):
    media_type = forms.ChoiceField(label="Tipo", choices=[])
    title = forms.CharField(label="Título", max_length=140, required=False)
    alt_text = forms.CharField(label="Texto alternativo", max_length=180, required=False)
    order = forms.IntegerField(label="Orden", min_value=0, initial=0)
    is_public = forms.BooleanField(label="Visible en catálogo público", required=False, initial=True)
    file = forms.FileField(label="Archivo", validators=[validate_upload_extension, validate_upload_size])

    def __init__(self, *args, **kwargs):
        from apps.vehicles.models import VehicleMedia
        super().__init__(*args, **kwargs)
        self.fields["media_type"].choices = VehicleMedia.MediaType.choices
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean(self):
        cleaned = super().clean()
        media_type = cleaned.get("media_type")
        uploaded_file = cleaned.get("file")
        if not media_type or not uploaded_file:
            return cleaned
        from apps.vehicles.models import VehicleMedia

        allowed_by_type = {
            VehicleMedia.MediaType.HERO: IMAGE_EXTENSIONS,
            VehicleMedia.MediaType.IMAGE: IMAGE_EXTENSIONS,
            VehicleMedia.MediaType.FALLBACK: IMAGE_EXTENSIONS,
            VehicleMedia.MediaType.MODEL_3D: MODEL_3D_EXTENSIONS,
            VehicleMedia.MediaType.VIDEO: VIDEO_EXTENSIONS,
            VehicleMedia.MediaType.MANUAL: DOCUMENT_EXTENSIONS - {".p12", ".pfx", ".csv", ".xls", ".xlsx"},
        }
        suffix = Path(uploaded_file.name).suffix.lower()
        if suffix not in allowed_by_type.get(media_type, set()):
            self.add_error("file", "La extensión del archivo no corresponde al tipo multimedia seleccionado.")
        return cleaned
