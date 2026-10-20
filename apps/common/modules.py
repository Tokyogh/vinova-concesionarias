"""ES: Este módulo implementa el componente modules para el dominio de infraestructura compartida.

EN: This module implements the modules component for the common domain.

Contexto existente / Existing context:
Modules support for the common domain.
"""

from __future__ import annotations

from django.conf import settings
from django.http import Http404


OPTIONAL_MODULE_SETTINGS = {
    "post_sales": "VINOVA_MODULE_POST_SALES_ENABLED",
}


def is_module_enabled(code: str) -> bool:
    setting_name = OPTIONAL_MODULE_SETTINGS.get(code)
    return bool(setting_name and getattr(settings, setting_name, False))


class OptionalModuleRequiredMixin:
    module_code: str | None = None

    def dispatch(self, request, *args, **kwargs):
        if not self.module_code or not is_module_enabled(self.module_code):
            raise Http404("Módulo no disponible.")
        return super().dispatch(request, *args, **kwargs)
