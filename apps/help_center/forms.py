"""ES: Este módulo define formularios y validación de entrada en backend para el dominio de ayuda.

EN: This module defines forms and server-side input validation for the help center domain.

Contexto existente / Existing context:
Server-side forms and input validation for the help center domain.
"""

from django import forms
from django.db.models import Q
from django.urls import NoReverseMatch, reverse

from apps.accounts.models import PermissionCode, Role
from apps.common.validators import validate_no_unsafe_control_characters
from apps.help_center.models import HelpArticle, HelpCategory


class HelpSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        max_length=120,
        label="Buscar",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Busca por módulo, tarea o palabra clave",
                "autocomplete": "off",
            }
        ),
    )


class HelpArticleForm(forms.ModelForm):
    """ES: Valida contenido administrable como texto seguro y referencias reales.

    EN: Validates managed content as safe text with real references.
    """

    role_codes = forms.CharField(
        label="Roles permitidos",
        required=False,
        help_text="Códigos de rol separados por comas. Vacío permite cualquier rol con acceso y permiso.",
    )
    change_note = forms.CharField(
        label="Motivo del cambio",
        max_length=220,
        required=True,
        widget=forms.Textarea(attrs={"rows": 2}),
    )

    class Meta:
        model = HelpArticle
        fields = [
            "category", "title", "slug", "summary", "content", "article_type",
            "route_name", "permission_code", "role_codes", "keywords",
            "estimated_minutes", "order", "is_featured", "is_published",
            "change_note",
        ]
        labels = {
            "category": "Categoría",
            "title": "Título",
            "slug": "Slug",
            "summary": "Resumen",
            "content": "Contenido",
            "article_type": "Tipo",
            "route_name": "Ruta contextual",
            "permission_code": "Permiso requerido para leer",
            "keywords": "Palabras clave",
            "estimated_minutes": "Minutos estimados",
            "order": "Orden",
            "is_featured": "Destacado",
            "is_published": "Publicado",
        }
        widgets = {
            "summary": forms.Textarea(attrs={"rows": 3}),
            "content": forms.Textarea(attrs={"rows": 16}),
        }
        help_texts = {
            "content": "Texto plano. Los saltos de línea se conservan y cualquier HTML se muestra escapado.",
            "route_name": "Nombre de URL Django sin argumentos, por ejemplo vehicles_internal:list.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        categories = HelpCategory.objects.filter(is_active=True)
        if self.instance.pk and self.instance.category_id:
            categories = HelpCategory.objects.filter(
                Q(is_active=True) | Q(pk=self.instance.category_id)
            )
        self.fields["category"].queryset = categories.order_by("order", "name")
        if self.instance.pk:
            self.initial["role_codes"] = ", ".join(self.instance.role_codes or [])
        for name in ("title", "summary", "content", "keywords", "change_note"):
            self.fields[name].validators.append(validate_no_unsafe_control_characters)
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")

    def clean_route_name(self):
        route_name = self.cleaned_data["route_name"].strip()
        if not route_name:
            return ""
        try:
            reverse(route_name)
        except NoReverseMatch as exc:
            raise forms.ValidationError("La ruta contextual no existe o requiere parámetros.") from exc
        return route_name

    def clean_permission_code(self):
        code = self.cleaned_data["permission_code"].strip()
        if code and not PermissionCode.objects.filter(code=code).exists():
            raise forms.ValidationError("Selecciona un permiso registrado en VINOVA PRO.")
        return code

    def clean_role_codes(self):
        raw = self.cleaned_data["role_codes"]
        codes = list(dict.fromkeys(part.strip() for part in raw.split(",") if part.strip()))
        if len(codes) > 20:
            raise forms.ValidationError("Registra como máximo 20 roles.")
        known = set(Role.objects.filter(code__in=codes, is_active=True).values_list("code", flat=True))
        unknown = [code for code in codes if code not in known]
        if unknown:
            raise forms.ValidationError(f"Roles inexistentes o inactivos: {', '.join(unknown)}.")
        return codes
