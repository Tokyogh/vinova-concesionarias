"""ES: Este módulo implementa el componente downloads para el dominio de documentos.

EN: This module implements the downloads component for the documents domain.

Contexto existente / Existing context:
Downloads support for the documents domain.
"""

from __future__ import annotations

import logging

from django.http import Http404

logger = logging.getLogger(__name__)


def open_private_file_or_404(field_file, *, context: str):
    """Abre un objeto privado sin filtrar detalles del proveedor al cliente."""
    try:
        return field_file.open("rb")
    except Exception as exc:  # noqa: BLE001 - el proveedor puede usar excepciones propias
        logger.warning("Falló la lectura de %s (%s).", context, exc.__class__.__name__)
        raise Http404("El archivo no está disponible temporalmente.") from exc
