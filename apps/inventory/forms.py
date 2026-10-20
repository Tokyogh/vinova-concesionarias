"""ES: Este módulo define formularios y validación de entrada en backend para el dominio de inventario.

EN: This module defines forms and server-side input validation for the inventory domain.

Contexto existente / Existing context:
Server-side forms and input validation for the inventory domain.
"""

from __future__ import annotations

from django import forms
from django.utils.text import slugify

from apps.accounts.scopes import accessible_branches_queryset
from apps.branches.models import Branch
from apps.inventory.models import (
    PUBLIC_CATALOG_ITEM_TYPES,
    BranchStock,
    InventoryCategory,
    InventoryItem,
    StockMovement,
)
from apps.common.form_widgets import configure_accessible_filter_fields, make_searchable_select
from apps.common.validators import validate_no_unsafe_control_characters, validate_nonnegative_decimal


class InventoryItemSearchForm(forms.Form):
    q = forms.CharField(required=False, label="Buscar", widget=forms.TextInput(attrs={"placeholder": "SKU, nombre, descripción o categoría..."}))
    status = forms.ChoiceField(required=False, label="Estado")
    item_type = forms.ChoiceField(required=False, label="Tipo")
    category = forms.ModelChoiceField(required=False, label="Categoría", queryset=InventoryCategory.objects.none())
    sort = forms.ChoiceField(required=False, label="Orden", choices=[
        ("", "Nombre A–Z"), ("name_desc", "Nombre Z–A"),
        ("stock_desc", "Stock: mayor a menor"), ("stock_asc", "Stock: menor a mayor"),
        ("newest", "Más recientes"),
    ])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["status"].choices = [("", "Todos los estados")] + list(InventoryItem.Status.choices)
        self.fields["item_type"].choices = [("", "Todos los tipos")] + list(InventoryItem.ItemType.choices)
        self.fields["category"].queryset = InventoryCategory.objects.filter(is_active=True).order_by("name")
        self.fields["category"].empty_label = "Todas las categorías"
        configure_accessible_filter_fields(self.fields)
        make_searchable_select(self.fields["category"], "Buscar categoría...")


class PublicInventoryCatalogFilterForm(forms.Form):
    """ES: Valida filtros públicos acotados. EN: Validates bounded public filters."""

    q = forms.CharField(
        required=False,
        max_length=80,
        label="Buscar",
        widget=forms.SearchInput(
            attrs={"placeholder": "Buscar repuesto, código o descripción...", "autocomplete": "off"}
        ),
    )
    category = forms.ChoiceField(required=False, label="Categoría")
    item_type = forms.ChoiceField(required=False, label="Tipo")
    sort = forms.ChoiceField(
        required=False,
        label="Orden",
        choices=[
            ("", "Más recientes"),
            ("name", "Nombre A–Z"),
            ("price_asc", "Precio: menor a mayor"),
            ("price_desc", "Precio: mayor a menor"),
        ],
    )

    def __init__(self, *args, categories=(), **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["category"].choices = [("", "Todas las categorías")] + [
            (category.slug, category.name) for category in categories
        ]
        type_labels = dict(InventoryItem.ItemType.choices)
        self.fields["item_type"].choices = [("", "Todos los tipos")] + [
            (type_code, type_labels[type_code]) for type_code in PUBLIC_CATALOG_ITEM_TYPES
        ]
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_q(self):
        return (self.cleaned_data.get("q") or "").strip()


class InventoryItemForm(forms.ModelForm):
    class Meta:
        model = InventoryItem
        fields = [
            "category",
            "name",
            "sku",
            "item_type",
            "description",
            "unit",
            "price",
            "cost",
            "image",
            "status",
            "is_public",
            "track_stock",
        ]
        labels = {
            "category": "Categoría",
            "name": "Nombre del artículo",
            "sku": "SKU",
            "item_type": "Tipo",
            "description": "Descripción",
            "unit": "Unidad de medida",
            "price": "Precio de venta",
            "cost": "Costo interno",
            "image": "Imagen",
            "status": "Estado",
            "is_public": "Visible para clientes cuando aplique",
            "track_stock": "Maneja stock físico",
        }
        widgets = {"description": forms.Textarea(attrs={"rows": 4})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("name", "description", "unit"):
            self.fields[name].validators.append(validate_no_unsafe_control_characters)
        for name in ("price", "cost"):
            self.fields[name].validators.append(validate_nonnegative_decimal)
            self.fields[name].widget.attrs.setdefault("min", "0")
        self.fields["category"].queryset = InventoryCategory.objects.filter(is_active=True).order_by("name")
        self.fields["category"].empty_label = "Sin categoría"
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        make_searchable_select(self.fields["category"], "Buscar categoría...")

    def clean_sku(self):
        sku = (self.cleaned_data.get("sku") or "").upper().strip()
        if not sku:
            raise forms.ValidationError("El SKU es obligatorio.")
        qs = InventoryItem.objects.filter(sku=sku)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ya existe un artículo con este SKU.")
        return sku


class InventoryCategoryForm(forms.ModelForm):
    class Meta:
        model = InventoryCategory
        fields = ["name", "slug", "parent", "description", "is_active"]
        labels = {"name": "Nombre", "slug": "Slug", "parent": "Categoría padre", "description": "Descripción", "is_active": "Activa"}
        widgets = {"description": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["parent"].queryset = InventoryCategory.objects.filter(is_active=True).order_by("name")
        self.fields["parent"].empty_label = "Sin categoría padre"
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        make_searchable_select(self.fields["parent"], "Buscar categoría padre...")

    def clean_slug(self):
        slug = self.cleaned_data.get("slug") or slugify(self.cleaned_data.get("name") or "")
        if not slug:
            raise forms.ValidationError("El slug es obligatorio.")
        qs = InventoryCategory.objects.filter(slug=slug)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Ya existe una categoría con este slug.")
        return slug


class StockMovementForm(forms.Form):
    item = forms.ModelChoiceField(label="Artículo", queryset=InventoryItem.objects.none())
    branch = forms.ModelChoiceField(label="Sucursal", queryset=Branch.objects.none())
    movement_type = forms.ChoiceField(label="Movimiento", choices=[
        (StockMovement.MovementType.IN, "Entrada: sumar al stock"),
        (StockMovement.MovementType.OUT, "Salida: descontar del stock"),
        (StockMovement.MovementType.ADJUST, "Ajuste: dejar stock exacto"),
    ])
    quantity = forms.DecimalField(label="Cantidad", min_value=0.01, max_digits=12, decimal_places=2)
    unit_cost = forms.DecimalField(label="Costo unitario", required=False, min_value=0, max_digits=12, decimal_places=2)
    reference = forms.CharField(label="Referencia", required=False, max_length=140, widget=forms.TextInput(attrs={"placeholder": "Factura, orden, guía, ajuste interno..."}))
    reason = forms.CharField(label="Motivo / observación", required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, **kwargs):
        item = kwargs.pop("item", None)
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["item"].queryset = InventoryItem.objects.filter(is_deleted=False, status=InventoryItem.Status.ACTIVE, track_stock=True).order_by("sku", "name")
        self.fields["branch"].queryset = accessible_branches_queryset(
            user,
            permission_codes=("inventory.manage_stock",),
        )
        if item is not None:
            self.fields["item"].queryset = InventoryItem.objects.filter(pk=item.pk)
            self.fields["item"].initial = item
            self.fields["item"].widget = forms.HiddenInput()
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        if not isinstance(self.fields["item"].widget, forms.HiddenInput):
            make_searchable_select(self.fields["item"], "Buscar artículo por SKU o nombre...")
        make_searchable_select(self.fields["branch"], "Buscar sucursal...")


class StockTransferForm(forms.Form):
    item = forms.ModelChoiceField(label="Artículo", queryset=InventoryItem.objects.none())
    origin_branch = forms.ModelChoiceField(label="Sucursal origen", queryset=Branch.objects.none())
    destination_branch = forms.ModelChoiceField(label="Sucursal destino", queryset=Branch.objects.none())
    quantity = forms.DecimalField(label="Cantidad a transferir", min_value=0.01, max_digits=12, decimal_places=2)
    reference = forms.CharField(label="Referencia", required=False, max_length=140, widget=forms.TextInput(attrs={"placeholder": "Guía, orden de transferencia o documento interno..."}))
    reason = forms.CharField(label="Motivo / observación", required=False, widget=forms.Textarea(attrs={"rows": 3}))

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["item"].queryset = InventoryItem.objects.filter(is_deleted=False, status=InventoryItem.Status.ACTIVE, track_stock=True).order_by("sku", "name")
        branches = accessible_branches_queryset(
            user,
            permission_codes=("inventory.manage_stock",),
        )
        self.fields["origin_branch"].queryset = branches
        self.fields["destination_branch"].queryset = branches
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
        make_searchable_select(self.fields["item"], "Buscar artículo por SKU o nombre...")
        make_searchable_select(self.fields["origin_branch"], "Buscar sucursal origen...")
        make_searchable_select(self.fields["destination_branch"], "Buscar sucursal destino...")

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("origin_branch") and cleaned.get("destination_branch") and cleaned["origin_branch"] == cleaned["destination_branch"]:
            self.add_error("destination_branch", "La sucursal destino debe ser diferente a la sucursal origen.")
        return cleaned


class BranchStockSettingsForm(forms.ModelForm):
    class Meta:
        model = BranchStock
        fields = ["minimum_stock", "location_code"]
        labels = {"minimum_stock": "Stock mínimo", "location_code": "Ubicación interna"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")
