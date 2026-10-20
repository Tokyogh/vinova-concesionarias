"""ES: Este módulo implementa el componente assist para el dominio de infraestructura compartida.

EN: This module implements the assist component for the common domain.

Contexto existente / Existing context:
Assist support for the common domain.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from unicodedata import category, normalize
from urllib.parse import urlencode

from django.urls import reverse

from apps.common.capabilities import (
    CAPABILITY_PERMISSION_CODES,
    allows_capability,
    permission_codes_for_user,
)
from apps.common.modules import is_module_enabled
from apps.common.navigation import ALL_DESTINATIONS

ALLOW_PERMISSION_CODES = CAPABILITY_PERMISSION_CODES


@dataclass(frozen=True)
class AssistIntent:
    key: str
    title: str
    description: str
    url_name: str
    allow: str
    keywords: tuple[str, ...] = field(default_factory=tuple)
    query: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    module: str | None = None

    def url(self) -> str:
        base = reverse(self.url_name)
        return f"{base}?{urlencode(self.query)}" if self.query else base


ASSIST_INTENTS = (
    AssistIntent(
        key="new_customer", title="Registrar cliente", url_name="customers_internal:create",
        allow="can_manage_customers", description="Abre el formulario autorizado para crear un cliente.",
        keywords=("nuevo cliente", "crear cliente", "registrar cliente", "alta cliente"),
    ),
    AssistIntent(
        key="new_vehicle", title="Registrar vehículo", url_name="vehicles_internal:create",
        allow="can_manage_vehicles", description="Abre el alta de una unidad en el inventario vehicular.",
        keywords=("nuevo vehiculo", "crear vehiculo", "registrar auto", "registrar unidad"),
    ),
    AssistIntent(
        key="new_sale", title="Crear cotización o venta", url_name="sales_internal:create",
        allow="can_manage_quotes", description="Inicia una operación comercial autorizada.",
        keywords=("nueva venta", "crear venta", "nueva cotizacion", "cotizar vehiculo"),
    ),
    AssistIntent(
        key="upload_document", title="Registrar documento", url_name="documents_internal:create",
        allow="can_manage_documents", description="Abre la carga protegida de documentos privados.",
        keywords=("registrar documento", "cargar documento", "subir archivo", "guardar contrato"),
    ),
    AssistIntent(
        key="low_stock", title="Ver stock bajo", url_name="inventory_internal:low_stock",
        allow="can_view_inventory", description="Muestra las alertas reales de reposición dentro de tu alcance.",
        keywords=("stock bajo", "faltantes", "reponer inventario", "alertas inventario"),
    ),
    AssistIntent(
        key="overdue_leads", title="Ver seguimientos vencidos", url_name="leads_internal:list",
        allow="can_view_leads", description="Prepara el filtro seguro de seguimientos vencidos del CRM.",
        keywords=("seguimientos vencidos", "leads atrasados", "tareas crm", "pendientes comerciales"),
        query=(("overdue", "on"),),
    ),
    AssistIntent(
        key="issue_invoice", title="Crear comprobante desde venta", url_name="invoices_internal:create_from_sale",
        allow="can_issue_invoices", description="Abre el flujo real de emisión desde una venta autorizada.",
        keywords=("crear factura", "emitir factura", "nuevo comprobante", "facturar venta"),
    ),
    AssistIntent(
        key="help", title="Abrir ayuda y capacitación", url_name="help_center:home",
        allow="can_view_help", description="Consulta guías y capacitación disponibles para tu cuenta.",
        keywords=("ayuda", "como usar", "capacitacion", "manual"),
    ),
)


def _normalized(value: str) -> str:
    value = normalize("NFD", (value or "").lower())
    ascii_value = "".join(char for char in value if category(char) != "Mn")
    return " ".join("".join(char if char.isalnum() else " " for char in ascii_value).split())


def _score(query: str, title: str, keywords) -> int:
    needle = _normalized(query)
    if not needle:
        return 1
    phrases = [_normalized(title), *(_normalized(item) for item in keywords)]
    if needle in phrases:
        return 120
    if any(needle in phrase for phrase in phrases):
        return 90
    stop_words = {"a", "al", "como", "de", "donde", "el", "en", "la", "las", "lo", "los", "para", "por", "puedo", "quiero", "un", "una", "y"}
    words = [word for word in needle.split() if len(word) > 2 and word not in stop_words]
    haystack = " ".join(phrases)
    matched = sum(word in haystack or word[:5] in haystack for word in words)
    return 50 + matched * 10 if words and matched == len(words) else 0


def _intent_allowed(intent: AssistIntent, user, modules, permission_codes) -> bool:
    if intent.module and not modules.get(intent.module, False):
        return False
    return allows_capability(intent.allow, user, permission_codes)


def assist_response_for_user(user, query: str) -> dict:
    """Resuelve ayuda/navegación sin datos comerciales ni acciones mutables."""
    query = (query or "").strip()[:160]
    permission_codes = permission_codes_for_user(user)
    modules = {
        "post_sales": bool(
            is_module_enabled("post_sales")
            and allows_capability("can_view_post_sales", user, permission_codes)
        )
    }
    candidates = []
    restricted_match = False

    for intent in ASSIST_INTENTS:
        score = _score(query, intent.title, intent.keywords)
        if not score:
            continue
        if not _intent_allowed(intent, user, modules, permission_codes):
            restricted_match = True
            continue
        candidates.append((score + 20, {
            "key": f"assist:{intent.key}", "title": intent.title,
            "description": intent.description, "url": intent.url(), "kind": "action",
            "area": "VINOVA Assist", "keywords": list(intent.keywords),
        }))

    for destination in ALL_DESTINATIONS.values():
        score = _score(query, destination.title, destination.keywords)
        if not score:
            continue
        if (destination.module and not modules.get(destination.module, False)) or not allows_capability(
            destination.allow, user, permission_codes
        ):
            restricted_match = True
            continue
        candidates.append((score, {
            "key": destination.key, "title": destination.title,
            "description": f"Ir a {destination.area} → {destination.title}.",
            "url": destination._url(), "kind": "destination", "area": destination.area,
            "keywords": list(destination.keywords),
        }))

    candidates.sort(key=lambda item: (-item[0], item[1]["title"]))
    results = [item for _, item in candidates[:8]]
    if results and restricted_match:
        answer = f"Encontré {len(results)} opción(es) autorizada(s). Alguna acción relacionada requiere permisos adicionales."
    elif results:
        answer = f"Encontré {len(results)} opción(es) autorizada(s) para tu consulta."
    elif restricted_match:
        answer = "La función existe, pero tu cuenta no tiene acceso. Solicita el permiso correspondiente."
    else:
        answer = "No encontré una ruta autorizada. Prueba con el nombre del área, la acción o consulta Ayuda."
    return {"query": query, "answer": answer, "results": results}
