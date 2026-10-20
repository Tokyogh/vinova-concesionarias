"""ES: Este módulo implementa servicios de negocio y efectos transaccionales para el dominio de reportes.

EN: This module implements business services and transactional effects for the reports domain.

Contexto existente / Existing context:
Transactional business services for the reports domain.
"""

from __future__ import annotations

import csv
from datetime import datetime
from io import BytesIO, StringIO

from django.http import HttpResponse
from django.utils import timezone

from apps.audit.services import audit_log
from apps.reports.models import ReportExportJob
from apps.reports import selectors


REPORT_LABELS = {
    "executive": "Resumen ejecutivo",
    "sales": "Ventas por fecha",
    "branches": "Ventas por sucursal",
    "vehicles": "Vehículos por estado",
    "inventory": "Inventario bajo",
    "stock_movements": "Movimientos de stock",
    "invoices": "Facturas emitidas",
    "customers": "Clientes nuevos",
    "activity": "Actividad de usuarios",
    "products": "Productos más vendidos",
}


def report_title(report_type):
    return REPORT_LABELS.get(report_type, "Reporte empresarial")


def filename_for(report_type, export_format):
    stamp = timezone.localtime().strftime("%Y%m%d_%H%M")
    return f"vinova_pro_{report_type}_{stamp}.{export_format}"


def get_report_context(report_type, filters, user):
    mapping = {
        "executive": selectors.executive_context,
        "sales": selectors.sales_context,
        "branches": selectors.branches_context,
        "vehicles": selectors.vehicles_context,
        "inventory": selectors.inventory_context,
        "stock_movements": selectors.inventory_context,
        "invoices": selectors.invoices_context,
        "customers": selectors.customers_context,
        "activity": selectors.activity_context,
        "products": selectors.products_context,
    }
    fn = mapping.get(report_type, selectors.executive_context)
    return fn(filters, user)


def rows_for_report(report_type, filters, user, *, limit=5000, offset=0):
    """ES: Ejecuta la operación «rows for report» dentro del dominio de reportes.

    EN: Executes the «rows for report» operation within the reports domain.
    """

    row_slice = slice(offset, offset + limit)
    if report_type == "sales":
        rows = selectors.sales_queryset(filters, user)
        headers = ["Número", "Tipo", "Estado", "Cliente", "Sucursal", "Asesor", "Total", "Pagado", "Saldo", "Creado"]
        data = [
            [s.number, s.get_kind_display(), s.get_status_display(), s.customer.display_name, s.branch.name, s.advisor.get_full_name() or s.advisor.username if s.advisor else "", s.total, s.amount_paid, s.balance_due, timezone.localtime(s.created_at).strftime("%Y-%m-%d %H:%M")]
            for s in rows[row_slice]
        ]
    elif report_type == "branches":
        ctx = selectors.branches_context(filters, user)
        headers = ["Sucursal", "Ciudad", "Ventas", "Total ventas", "Facturas", "Total facturas", "Vehículos disponibles", "Stock bajo"]
        data = [
            [x["branch"].name, x["branch"].city, x["sales_count"], x["sales_total"], x["invoices_count"], x["invoices_total"], x["available_vehicles"], x["low_stock"]]
            for x in ctx["branch_cards"][row_slice]
        ]
    elif report_type == "vehicles":
        rows = selectors.vehicles_queryset(filters, user)
        headers = ["Marca", "Modelo", "Año", "Versión", "Código interno", "VIN real", "Placa", "Estado", "Sucursal", "Precio", "Destacado"]
        data = [[v.brand.name, v.model.name, v.year, v.version, v.internal_code, v.vin or "", v.plate, v.get_status_display(), v.branch.name if v.branch else "", v.price or "", "Sí" if v.is_featured else "No"] for v in rows[row_slice]]
    elif report_type == "inventory":
        rows = selectors.low_stock_queryset(filters, user)
        headers = ["SKU", "Artículo", "Categoría", "Sucursal", "Stock", "Reservado", "Disponible", "Mínimo", "Ubicación"]
        data = [[r.item.sku, r.item.name, r.item.category.name if r.item.category else "", r.branch.name, r.quantity, r.reserved_quantity, r.available_quantity, r.minimum_stock, r.location_code] for r in rows[row_slice]]
    elif report_type == "stock_movements":
        rows = selectors.stock_movements_queryset(filters, user)
        headers = ["Fecha", "Tipo", "SKU", "Artículo", "Sucursal", "Destino", "Cantidad", "Referencia", "Usuario", "Motivo"]
        data = [
            [timezone.localtime(m.created_at).strftime("%Y-%m-%d %H:%M"), m.get_movement_type_display(), m.item.sku, m.item.name, m.branch.name, m.destination_branch.name if m.destination_branch else "", m.quantity, m.reference, m.created_by.username if m.created_by else "", m.reason]
            for m in rows[row_slice]
        ]
    elif report_type == "invoices":
        rows = selectors.invoices_queryset(filters, user)
        headers = ["Número", "Tipo", "Estado", "Cliente", "Documento", "Sucursal", "Fecha", "Total", "Pagado", "Saldo"]
        data = [[i.number, i.get_invoice_type_display(), i.get_status_display(), i.customer_name, i.customer_document, i.branch.name, i.issue_date.isoformat(), i.total, i.amount_paid, i.balance_due] for i in rows[row_slice]]
    elif report_type == "customers":
        rows = selectors.customers_queryset(filters, user)
        headers = ["Cliente", "Tipo", "Estado", "Documento", "Email", "Teléfono", "Ciudad", "Sucursal", "Asesor", "Creado"]
        data = [[c.display_name, c.get_customer_type_display(), c.get_status_display(), c.identification_number or "", c.email, c.phone, c.city, c.assigned_branch.name if c.assigned_branch else "", c.assigned_advisor.username if c.assigned_advisor else "", timezone.localtime(c.created_at).strftime("%Y-%m-%d %H:%M")] for c in rows[row_slice]]
    elif report_type == "activity":
        rows = selectors.activity_queryset(filters, user)
        headers = ["Fecha", "Usuario", "Acción", "Modelo", "Objeto", "ID", "IP"]
        data = [[timezone.localtime(a.created_at).strftime("%Y-%m-%d %H:%M"), a.user.username if a.user else "Sistema", a.action, a.content_type_label, a.object_repr, a.object_id, a.ip_address or ""] for a in rows[row_slice]]
    elif report_type == "products":
        ctx = selectors.products_context(filters, user)
        headers = ["SKU", "Artículo", "Descripción", "Líneas", "Cantidad", "Total"]
        data = [[r.get("item__sku") or "", r.get("item__name") or "", r.get("description") or "", r.get("count") or 0, r.get("quantity") or 0, r.get("total") or 0] for r in ctx["product_rows"][row_slice]]
    else:
        ctx = selectors.executive_context(filters, user)
        headers = ["Indicador", "Valor"]
        data = [[k, v] for k, v in ctx["metrics"].items()]
    return report_title(report_type), headers, data


def create_export_job(*, report_type, export_format, filters, user):
    return ReportExportJob.objects.create(
        report_type=report_type,
        export_format=export_format,
        status=ReportExportJob.Status.RUNNING,
        filters=selectors.filters_as_json(filters),
        requested_by=user if getattr(user, "is_authenticated", False) else None,
    )


def export_csv_response(report_type, filters, user):
    title, headers, rows = rows_for_report(report_type, filters, user)
    filename = filename_for(report_type, "csv")
    job = create_export_job(report_type=report_type, export_format=ReportExportJob.ExportFormat.CSV, filters=filters, user=user)
    buffer = StringIO()
    writer = csv.writer(buffer)
    writer.writerow([title])
    writer.writerow(["Generado", datetime.now().strftime("%Y-%m-%d %H:%M")])
    writer.writerow(["Rango", f"{filters['start_date']} - {filters['end_date']}"])
    writer.writerow([])
    writer.writerow(headers)
    writer.writerows(rows)
    job.mark_completed(row_count=len(rows), file_name=filename)
    audit_log(user=user, action="reports.export_csv", target=job, metadata={"report_type": report_type, "rows": len(rows)})
    response = HttpResponse(buffer.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def export_xlsx_response(report_type, filters, user):
    try:
        from openpyxl import Workbook
    except Exception:  # pragma: no cover - depends on optional runtime package
        response = HttpResponse(
            "La exportación Excel requiere instalar openpyxl. Ejecuta: pip install openpyxl o agrega openpyxl a requirements/base.txt.",
            status=501,
            content_type="text/plain; charset=utf-8",
        )
        return response
    title, headers, rows = rows_for_report(report_type, filters, user)
    filename = filename_for(report_type, "xlsx")
    job = create_export_job(report_type=report_type, export_format=ReportExportJob.ExportFormat.XLSX, filters=filters, user=user)
    wb = Workbook()
    ws = wb.active
    ws.title = "Reporte"
    ws.append([title])
    ws.append(["Generado", datetime.now().strftime("%Y-%m-%d %H:%M")])
    ws.append(["Rango", f"{filters['start_date']} - {filters['end_date']}"])
    ws.append([])
    ws.append(headers)
    for row in rows:
        ws.append(list(row))
    for column in ws.columns:
        max_length = max(len(str(cell.value or "")) for cell in column)
        ws.column_dimensions[column[0].column_letter].width = min(max(max_length + 2, 12), 42)
    stream = BytesIO()
    wb.save(stream)
    job.mark_completed(row_count=len(rows), file_name=filename)
    audit_log(user=user, action="reports.export_xlsx", target=job, metadata={"report_type": report_type, "rows": len(rows)})
    response = HttpResponse(stream.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
