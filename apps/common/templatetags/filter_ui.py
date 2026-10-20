"""ES: Este módulo implementa el componente filter ui para el dominio de infraestructura compartida.

EN: This module implements the filter ui component for the common domain.

Contexto existente / Existing context:
Filter ui support for the common domain.
"""

from __future__ import annotations

from urllib.parse import urlencode

from django import template


register = template.Library()


def _field_names(value):
    return [name.strip() for name in (value or "").split(",") if name.strip()]


def _display_value(bound_field, value):
    if value in (None, ""):
        return ""
    field = bound_field.field
    if hasattr(field, "queryset"):
        try:
            return str(field.queryset.get(pk=value))
        except (field.queryset.model.DoesNotExist, ValueError, TypeError):
            return str(value)
    choices = dict(field.choices) if getattr(field, "choices", None) else {}
    if value in choices:
        return str(choices[value])
    if value is True or value == "on":
        return "Sí"
    return str(value)


@register.inclusion_tag("components/filter_panel.html", takes_context=True)
def vinova_filter_panel(context, form, clear_url, namespace, common="q,status,sort", advanced=""):
    request = context["request"]
    common_names = _field_names(common)
    advanced_names = _field_names(advanced)
    known_names = common_names + advanced_names
    common_fields = [form[name] for name in common_names if name in form.fields]
    advanced_fields = [form[name] for name in advanced_names if name in form.fields]
    chips = []
    advanced_active = False
    for name in known_names:
        if name not in form.fields:
            continue
        raw_value = request.GET.get(name, "")
        if raw_value in ("", None):
            continue
        query = request.GET.copy()
        query.pop(name, None)
        query.pop("page", None)
        href = request.path + (f"?{query.urlencode()}" if query else "")
        bound_field = form[name]
        chips.append({"label": bound_field.label, "value": _display_value(bound_field, raw_value), "href": href})
        advanced_active = advanced_active or name in advanced_names
    return {
        "form": form,
        "common_fields": common_fields,
        "advanced_fields": advanced_fields,
        "advanced_active": advanced_active,
        "chips": chips,
        "clear_url": clear_url,
        "namespace": namespace,
        "user_id": request.user.pk,
    }


@register.simple_tag(takes_context=True)
def filter_querystring(context, **kwargs):
    query = context["request"].GET.copy()
    for key, value in kwargs.items():
        if value in (None, ""):
            query.pop(key, None)
        else:
            query[key] = value
    return "?" + urlencode(query, doseq=True) if query else ""
