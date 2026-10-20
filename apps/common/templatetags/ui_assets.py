"""ES: Este módulo implementa el componente ui assets para el dominio de infraestructura compartida.

EN: This module implements the ui assets component for the common domain.

Contexto existente / Existing context:
Optional, final visual assets for public VINOVA UI slots.

Assets are activated by adding the documented file to ``static/img/vinova``.
Until then the page keeps its existing CSS slot and fallback without issuing a
request for a missing image.
"""

from django import template
from django.contrib.staticfiles import finders
from django.templatetags.static import static

register = template.Library()

FINAL_ASSETS = {
    "brand-logo": "img/vinova/vinova-symbol.svg",
    "dashboard-welcome": "img/vinova/01_dashboard-welcome.webp",
    "home-hero": "img/vinova/02_hero-home.webp",
    "vehicle-catalog-blue": "img/vinova/03_vehicle-catalog-blue.webp",
    "vehicle-catalog-silver": "img/vinova/04_vehicle-catalog-silver.webp",
    "vehicle-catalog-dark": "img/vinova/05_vehicle-catalog-dark.webp",
    "workshop-services": "img/vinova/06_workshop-services.webp",
    "showroom-about": "img/vinova/07_showroom-about.webp",
    "contact-branch": "img/vinova/08_contact-location.webp",
    "auth-cover": "img/vinova/09_auth-cover.webp",
}

FINAL_ASSET_WIDTHS = (640, 960)
FINAL_ASSET_NATIVE_WIDTHS = {
    "dashboard-welcome": 1669,
    "home-hero": 1672,
    "vehicle-catalog-blue": 1671,
    "vehicle-catalog-silver": 1672,
    "vehicle-catalog-dark": 1670,
    "workshop-services": 1670,
    "showroom-about": 1670,
    "contact-branch": 1670,
    "auth-cover": 1670,
}


@register.simple_tag
def ui_final_asset(slot: str) -> str:
    """Return a URL only when a known final-asset slot has a real file."""
    path = FINAL_ASSETS.get(slot)
    if not path or not finders.find(path):
        return ""
    return static(path)


@register.simple_tag
def ui_final_srcset(slot: str) -> str:
    """Return only responsive variants that are present in staticfiles."""
    path = FINAL_ASSETS.get(slot)
    if not path:
        return ""
    stem, suffix = path.rsplit(".", 1)
    candidates = []
    for width in FINAL_ASSET_WIDTHS:
        variant = f"{stem}-{width}.{suffix}"
        if finders.find(variant):
            candidates.append(f"{static(variant)} {width}w")
    native_width = FINAL_ASSET_NATIVE_WIDTHS.get(slot)
    if native_width and finders.find(path):
        candidates.append(f"{static(path)} {native_width}w")
    return ", ".join(candidates)
