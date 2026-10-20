"""ES: Este módulo implementa el componente pdf para el dominio de facturación.

EN: This module implements the pdf component for the invoices domain.

Contexto existente / Existing context:
PDF rendering for the invoices domain.
"""

from __future__ import annotations

from decimal import Decimal
from textwrap import wrap


def _pdf_text(value) -> str:
    text = str(value or "").encode("latin-1", "replace").decode("latin-1")
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def _money(value) -> str:
    return f"{Decimal(value or 0):,.2f}"


def _invoice_lines(invoice) -> list[str]:
    lines = [
        "VINOVA PRO - COMPROBANTE",
        f"Numero: {invoice.number}",
        f"Tipo: {invoice.get_invoice_type_display()}",
        f"Fecha de emision: {invoice.issue_date:%d/%m/%Y}",
        f"Empresa: {invoice.company.commercial_name or invoice.company.legal_name}",
        f"Sucursal: {invoice.branch.name}",
        "",
        f"Cliente: {invoice.customer_name}",
        f"Identificacion: {invoice.customer_document or 'N/D'}",
        f"Correo: {invoice.customer_email or 'N/D'}",
        "",
        "DETALLE",
    ]
    for item in invoice.lines.all():
        description = " ".join(str(item.description).split())
        prefix = f"{item.quantity} x {description}"
        wrapped = wrap(prefix, width=66) or [prefix]
        lines.extend(wrapped[:-1])
        lines.append(f"{wrapped[-1]}  USD {_money(item.line_total)}")
    lines.extend(
        [
            "",
            f"Subtotal: USD {_money(invoice.subtotal)}",
            f"Descuento: USD {_money(invoice.discount_total)}",
            f"Impuestos: USD {_money(invoice.tax_total)}",
            f"TOTAL: USD {_money(invoice.total)}",
        ]
    )
    if invoice.notes:
        lines.extend(["", "Observaciones:", *wrap(" ".join(invoice.notes.split()), width=78)])
    lines.extend(["", "Documento interno VINOVA. No constituye autorizacion tributaria SRI."])
    return lines[:52]


def render_invoice_pdf(invoice) -> bytes:
    """Render a deterministic PDF without external binaries or network calls."""
    commands = [
        "q",
        "0.075 0.165 0.290 rg",
        "36 754 523 58 re f",
        "Q",
        "BT",
        "/F2 18 Tf",
        "1 1 1 rg",
        "1 0 0 1 52 785 Tm",
        "(VINOVA PRO - COMPROBANTE) Tj",
        "/F1 9 Tf",
        "1 0 0 1 52 767 Tm",
        f"({_pdf_text(invoice.number)} - documento privado) Tj",
        "ET",
    ]
    y = 726
    for line in _invoice_lines(invoice)[1:]:
        font = "/F1 10 Tf"
        color = "0.10 0.13 0.18 rg"
        if line == "DETALLE":
            font = "/F2 11 Tf"
            color = "0.075 0.165 0.290 rg"
            y -= 4
        elif line.startswith("TOTAL:"):
            font = "/F2 12 Tf"
        commands.extend(
            [
                "BT",
                font,
                color,
                f"1 0 0 1 48 {y} Tm",
                f"({_pdf_text(line)}) Tj",
                "ET",
            ]
        )
        y -= 14 if line else 11
    commands.extend(
        [
            "0.72 0.75 0.80 RG",
            "48 52 m 547 52 l S",
            "BT",
            "/F1 8 Tf",
            "0.35 0.39 0.45 rg",
            "1 0 0 1 48 36 Tm",
            "(Generado por VINOVA PRO - descarga privada auditada) Tj",
            "ET",
        ]
    )
    stream = "\n".join(commands).encode("latin-1")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 5 0 R /F2 6 0 R >> >> /Contents 4 0 R >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold /Encoding /WinAnsiEncoding >>",
    ]
    output = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for number, body in enumerate(objects, start=1):
        offsets.append(len(output))
        output.extend(f"{number} 0 obj\n".encode("ascii"))
        output.extend(body)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    output.extend(
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode(
            "ascii"
        )
    )
    return bytes(output)
