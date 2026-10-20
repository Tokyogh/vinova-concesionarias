"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for write flows in the deployment_smoke domain.
"""

from __future__ import annotations

import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

from tests.deployment_smoke.helpers.assertions import (
    fill_if_present,
    select_first_nonempty,
    select_value_if_present,
)
from tests.deployment_smoke.helpers.forms import id_from_detail_url, select_matching_vehicle_catalog, submit_and_wait
from tests.deployment_smoke.helpers.models import CreatedResource
from tests.deployment_smoke.helpers.runtime import run_check, skip_check

__test__ = False

WRITE_SCENARIOS = {"customers", "vehicles", "inventory", "sales", "documents"}


def run_scenario(state, session, scenario: str):  # noqa: ANN001
    if not state.config.write_tests:
        return skip_check(
            state,
            code=f"{scenario}.write_disabled",
            scenario=scenario,
            title=f"Flujo de escritura: {scenario}",
            message="Las escrituras no fueron habilitadas explícitamente.",
            required=state.config.mode in {"staging", "demo"},
        )
    callbacks = {
        "customers": lambda: _customer(state, session),
        "vehicles": lambda: _vehicle(state, session),
        "inventory": lambda: _inventory(state, session),
        "sales": lambda: _sales_and_lead(state, session),
        "documents": lambda: _document(state, session),
    }
    return run_check(
        state,
        code=f"{scenario}.write_flow",
        scenario=scenario,
        title=f"Creación, consulta y actualización: {scenario}",
        callback=callbacks[scenario],
    )


def _customer(state, session) -> dict:  # noqa: ANN001
    marker = state.config.marker
    page = session.goto("/dashboard/customers/new/")
    select_value_if_present(page, "customer_type", "natural")
    fill_if_present(page, "first_name", f"Cliente {marker}")
    fill_if_present(page, "last_name", "QA")
    fill_if_present(page, "email", f"smoke-{state.config.run_id}@example.invalid")
    fill_if_present(page, "phone", "0999999999")
    fill_if_present(page, "source", marker)
    fill_if_present(page, "internal_notes", f"Dato ficticio {marker}")
    submit_and_wait(page, "Guardar cliente")
    customer_id = id_from_detail_url(page.url, "/dashboard/customers")
    detail = f"/dashboard/customers/{customer_id}/"
    state.register_resource(
        CreatedResource(
            kind="customer",
            label=f"Cliente {marker}",
            detail_url=detail,
            cleanup_action=f"/dashboard/customers/{customer_id}/status/archive/",
            cleanup_button="Archivar",
        )
    )
    page = session.goto(f"/dashboard/customers/{customer_id}/edit/")
    fill_if_present(page, "city", "Quito QA")
    submit_and_wait(page, "Guardar cliente")
    if marker not in page.locator("body").inner_text():
        raise AssertionError("El cliente SMOKE no aparece en su detalle.")
    session.goto(f"/dashboard/customers/?q={marker}")
    if marker not in session.page.locator("body").inner_text():
        raise AssertionError("La búsqueda no encontró el cliente SMOKE.")
    shot = session.screenshot("customer-smoke")
    state.metadata["customer_id"] = customer_id
    return {"customer_id": customer_id, "evidence": [shot]}


def _vehicle(state, session) -> dict:  # noqa: ANN001
    marker = state.config.marker
    page = session.goto("/dashboard/vehicles/new/")
    select_matching_vehicle_catalog(page)
    fill_if_present(page, "year", "2026")
    fill_if_present(page, "version", marker)
    fill_if_present(page, "plate", f"SMK{state.config.run_id[-5:].upper()}")
    fill_if_present(page, "color", "Azul QA")
    fill_if_present(page, "mileage", "0")
    fill_if_present(page, "price", "1000")
    fill_if_present(page, "short_description", f"Vehículo ficticio {marker}")
    fill_if_present(page, "description", f"Validación automatizada {marker}")
    select_value_if_present(page, "status", "available")
    submit_and_wait(page, "Guardar vehículo")
    vehicle_id = id_from_detail_url(page.url, "/dashboard/vehicles")
    detail = f"/dashboard/vehicles/{vehicle_id}/"
    state.register_resource(
        CreatedResource(
            kind="vehicle",
            label=f"Vehículo {marker}",
            detail_url=detail,
            cleanup_action=f"/dashboard/vehicles/{vehicle_id}/archive/",
            cleanup_button="Archivar",
        )
    )
    page = session.goto(f"/dashboard/vehicles/{vehicle_id}/edit/")
    fill_if_present(page, "color", "Gris QA")
    submit_and_wait(page, "Guardar vehículo")
    session.goto(f"/dashboard/vehicles/?q={marker}")
    if marker not in session.page.locator("body").inner_text():
        raise AssertionError("La búsqueda no encontró el vehículo SMOKE.")
    shot = session.screenshot("vehicle-smoke")
    state.metadata["vehicle_id"] = vehicle_id
    return {"vehicle_id": vehicle_id, "evidence": [shot]}


def _inventory(state, session) -> dict:  # noqa: ANN001
    marker = state.config.marker
    page = session.goto("/dashboard/inventory/new/")
    fill_if_present(page, "name", f"Artículo {marker}")
    fill_if_present(page, "sku", marker)
    select_value_if_present(page, "item_type", "spare_part") or select_first_nonempty(page, "item_type")
    fill_if_present(page, "description", f"Artículo ficticio {marker}")
    fill_if_present(page, "unit", "unidad")
    fill_if_present(page, "price", "25")
    fill_if_present(page, "cost", "10")
    select_value_if_present(page, "status", "active")
    track = page.locator("input[name='track_stock']")
    if track.count() and not track.is_checked():
        track.check()
    submit_and_wait(page, "Guardar artículo")
    item_id = id_from_detail_url(page.url, "/dashboard/inventory")
    detail = f"/dashboard/inventory/{item_id}/"
    state.register_resource(
        CreatedResource(
            kind="inventory",
            label=f"Artículo {marker}",
            detail_url=detail,
            cleanup_action=f"/dashboard/inventory/{item_id}/archive/",
            cleanup_button="Archivar",
        )
    )
    form = page.locator("form.inventory-inline-form")
    if form.count() == 0:
        raise AssertionError("El detalle no contiene el formulario de movimiento de stock.")
    branch_value = select_first_nonempty(page, "branch")
    select_value_if_present(page, "movement_type", "in")
    fill_if_present(page, "quantity", "2")
    fill_if_present(page, "reference", marker)
    submit_and_wait(page, "Guardar movimiento")
    if "2" not in page.locator("body").inner_text():
        raise AssertionError("No se pudo confirmar el movimiento de entrada.")

    if not select_value_if_present(page, "branch", branch_value):
        raise AssertionError("La sucursal usada en la entrada ya no está disponible para validar la salida.")
    select_value_if_present(page, "movement_type", "out")
    fill_if_present(page, "quantity", "999999")
    fill_if_present(page, "reference", f"NEG-{marker}")
    submit_and_wait(page, "Guardar movimiento")
    body = page.locator("body").inner_text().lower()
    if "stock suficiente" not in body and "no se pudo registrar" not in body and "consumiría stock reservado" not in body:
        raise AssertionError("La aplicación no mostró rechazo verificable para stock negativo.")
    shot = session.screenshot("inventory-smoke")
    state.metadata["inventory_id"] = item_id
    return {"inventory_id": item_id, "negative_stock_blocked": True, "evidence": [shot]}


def _sales_and_lead(state, session) -> dict:  # noqa: ANN001
    marker = state.config.marker
    if not state.metadata.get("customer_id"):
        _customer(state, session)
    page = session.goto("/dashboard/leads/new/")
    select_value_if_present(page, "request_type", "quote")
    select_value_if_present(page, "status", "new")
    select_value_if_present(page, "priority", "high")
    select_value_if_present(page, "source", "showroom")
    fill_if_present(page, "full_name", f"Lead {marker}")
    fill_if_present(page, "email", f"lead-{state.config.run_id}@example.invalid")
    fill_if_present(page, "internal_notes", marker)
    submit_and_wait(page, "Guardar lead")
    lead_id = id_from_detail_url(page.url, "/dashboard/leads")
    state.register_resource(
        CreatedResource(
            kind="lead",
            label=f"Lead {marker}",
            detail_url=f"/dashboard/leads/{lead_id}/",
            cleanup_action=f"/dashboard/leads/{lead_id}/status/",
            cleanup_button="Actualizar etapa",
        )
    )

    page = session.goto("/dashboard/sales/new/")
    select_value_if_present(page, "kind", "reservation") or select_first_nonempty(page, "kind")
    customer_select = page.locator("select[name='customer']")
    options = customer_select.locator("option").evaluate_all(
        "opts => opts.map(o => ({value:o.value,text:(o.textContent||'').trim()})).filter(o => o.value)"
    )
    match = next((item for item in options if marker.lower() in item["text"].lower()), None)
    if not match:
        raise AssertionError("La venta no pudo localizar el cliente creado por este run_id.")
    customer_select.select_option(str(match["value"]))
    select_first_nonempty(page, "branch")
    select_value_if_present(page, "source", "showroom") or select_first_nonempty(page, "source")
    fill_if_present(page, "vehicle_price", "1000")
    fill_if_present(page, "vehicle_discount", "0")
    fill_if_present(page, "tax_rate", "15")
    reserved_until = (datetime.now(UTC) + timedelta(days=7)).strftime("%Y-%m-%dT%H:%M")
    fill_if_present(page, "reserved_until", reserved_until)
    fill_if_present(page, "notes", marker)
    fill_if_present(page, "internal_notes", marker)
    submit_and_wait(page, None)
    sale_id = id_from_detail_url(page.url, "/dashboard/sales")
    state.register_resource(
        CreatedResource(
            kind="sale",
            label=f"Venta {marker}",
            detail_url=f"/dashboard/sales/{sale_id}/",
            cleanup_action=f"/dashboard/sales/{sale_id}/action/cancel/",
            cleanup_button="Cancelar",
        )
    )
    if marker not in page.locator("body").inner_text():
        raise AssertionError("La venta no conserva la referencia SMOKE.")

    invoice_page = session.goto(f"/dashboard/invoices/new/?sale={sale_id}")
    sale_select = invoice_page.locator("select[name='sale']")
    available_sales = sale_select.locator("option").evaluate_all(
        "opts => opts.map(o => String(o.value)).filter(Boolean)"
    )
    if str(sale_id) not in available_sales:
        raise AssertionError("La reserva SMOKE no quedó disponible para facturación.")
    sale_select.select_option(str(sale_id))
    fill_if_present(invoice_page, "issue_date", datetime.now(UTC).date().isoformat())
    fill_if_present(invoice_page, "internal_notes", marker)
    submit_and_wait(invoice_page, "Crear borrador")
    invoice_id = id_from_detail_url(invoice_page.url, "/dashboard/invoices")
    state.register_resource(
        CreatedResource(
            kind="invoice",
            label=f"Factura {marker}",
            detail_url=f"/dashboard/invoices/{invoice_id}/",
            cleanup_action=f"/dashboard/invoices/{invoice_id}/action/void/",
            cleanup_button="Anular",
        )
    )

    duplicate_page = session.goto(f"/dashboard/invoices/new/?sale={sale_id}")
    duplicate_values = duplicate_page.locator("select[name='sale'] option").evaluate_all(
        "opts => opts.map(o => String(o.value)).filter(Boolean)"
    )
    if str(sale_id) in duplicate_values:
        raise AssertionError("La misma operación sigue disponible para crear una factura duplicada.")

    session.goto(f"/dashboard/invoices/{invoice_id}/")
    shot = session.screenshot("sales-and-invoices-smoke")
    state.metadata.update({"lead_id": lead_id, "sale_id": sale_id, "invoice_id": invoice_id})
    return {
        "lead_id": lead_id,
        "sale_id": sale_id,
        "invoice_id": invoice_id,
        "duplicate_invoice_blocked": True,
        "evidence": [shot],
    }


def _document(state, session) -> dict:  # noqa: ANN001
    marker = state.config.marker
    pdf = (
        b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Count 0>>endobj\ntrailer<</Root 1 0 R>>\n%%EOF\n"
    )
    with tempfile.TemporaryDirectory(prefix="vinova-smoke-") as temp_dir:
        pdf_path = Path(temp_dir) / f"Documento-{marker}.pdf"
        invalid_path = Path(temp_dir) / f"Documento-{marker}.exe"
        pdf_path.write_bytes(pdf)
        invalid_path.write_bytes(b"VINOVA deployment smoke invalid extension")
        page = session.goto("/dashboard/documents/upload/")
        fill_if_present(page, "title", f"Documento {marker}")
        select_value_if_present(page, "document_type", "other") or select_first_nonempty(page, "document_type")
        select_value_if_present(page, "status", "active")
        branch = page.locator("select[name='branch']")
        if branch.count():
            select_first_nonempty(page, "branch", required=False)
        fill_if_present(page, "notes", marker)

        page.locator("input[name='file']").set_input_files(str(invalid_path))
        submit_and_wait(page, "Guardar documento")
        invalid_body = page.locator("body").inner_text().lower()
        if "/dashboard/documents/upload/" not in page.url or (
            "extensión no permitida" not in invalid_body and "extension no permitida" not in invalid_body
        ):
            raise AssertionError("La carga no rechazó de forma verificable una extensión inválida.")

        page.locator("input[name='file']").set_input_files(str(pdf_path))
        submit_and_wait(page, "Guardar documento")
        document_id = id_from_detail_url(page.url, "/dashboard/documents")
        state.register_resource(
            CreatedResource(
                kind="document",
                label=f"Documento {marker}",
                detail_url=f"/dashboard/documents/{document_id}/",
                cleanup_action=f"/dashboard/documents/{document_id}/archive/",
                cleanup_button="Archivar",
            )
        )
        if marker not in page.locator("body").inner_text():
            raise AssertionError("El documento creado no aparece en su detalle.")
        shot = session.screenshot("document-smoke")
        state.metadata["document_id"] = document_id
        return {"document_id": document_id, "invalid_extension_blocked": True, "evidence": [shot]}
