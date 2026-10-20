"""ES: Este módulo implementa el componente form widgets para el dominio de infraestructura compartida.

EN: This module implements the form widgets component for the common domain.

Contexto existente / Existing context:
Form widgets support for the common domain.
"""

from __future__ import annotations


def make_searchable_select(field, placeholder="Buscar en la lista..."):
    """Progressive enhancement for large selects.

    The form remains a normal Django select if JavaScript is disabled. With JS,
    Vinova adds a search box above the select to avoid scrolling through very
    large lists.
    """

    field.widget.attrs.setdefault("class", "form-control")
    field.widget.attrs["data-searchable-select"] = "true"
    field.widget.attrs["data-search-placeholder"] = placeholder
    return field


def configure_accessible_filter_fields(fields):
    """Apply consistent styling and accessible names to compact filter forms.

    Internal list templates render filter widgets directly to keep toolbars
    compact. Because the Django ``label`` element is not rendered there, every
    control must carry its own accessible name.
    """

    for name, field in fields.items():
        field.widget.attrs.setdefault("class", "form-control")
        field.widget.attrs.setdefault(
            "aria-label",
            field.label or name.replace("_", " ").title(),
        )
    return fields
