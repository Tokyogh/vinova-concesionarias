"""ES: Este módulo implementa el componente templates para el dominio de importaciones.

EN: This module implements the templates component for the imports domain.

Contexto existente / Existing context:
Templates support for the imports domain.
"""

from __future__ import annotations

from typing import Any

from django.utils import timezone
from openpyxl import Workbook
from openpyxl.comments import Comment
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Protection, Side
from openpyxl.utils import get_column_letter
from openpyxl.workbook.defined_name import DefinedName
from openpyxl.worksheet.datavalidation import DataValidation

from apps.branches.models import Branch
from apps.imports.models import ImportBatch
from apps.imports.parsing import (
    CUSTOMER_STATUS_MAP,
    CUSTOMER_TYPE_MAP,
    IDENTIFICATION_MAP,
    ITEM_STATUS_MAP,
    ITEM_TYPE_MAP,
    MAX_VEHICLE_YEAR_OFFSET,
    MIN_VEHICLE_YEAR,
    VEHICLE_REQUIRED_HEADERS,
    VEHICLE_STATUS_MAP,
)
def sample_template_rows(import_type: str) -> tuple[list[str], list[list[Any]]]:
    if import_type == ImportBatch.ImportType.VEHICLES:
        return [
            "marca", "modelo", "año", "codigo_interno", "vin", "placa", "version", "color", "kilometraje", "precio", "estado",
            "sucursal_codigo", "publicar_en_catalogo", "destacado", "resumen", "descripcion_publica",
            "motor", "transmision", "seguridad", "interior", "tecnologia", "garantia", "consumo", "capacidad", "etiquetas",
        ], [[
            "Chevrolet", "Camaro", 2024, "", "1G1FH1R79R0100001", "ABC1234", "RS", "Negro", 0, "65000.00", "Disponible",
            "quito-norte", "si", "si", "Coupé deportivo listo para catálogo", "Ficha comercial del vehículo visible en el catálogo público.",
            "Motor V8 6.2L", "Automática", "Airbags y control de estabilidad", "Asientos deportivos", "Pantalla táctil y conectividad", "3 años", "Según versión", "4 pasajeros", "deportivo, premium",
        ]]
    if import_type == ImportBatch.ImportType.CUSTOMERS:
        return ["tipo", "identificacion_tipo", "identificacion", "nombres", "apellidos", "razon_social", "email", "telefono", "whatsapp", "ciudad", "provincia", "direccion", "fuente"], [["natural", "cedula", "0102030405", "Pepe", "Mora", "", "pepe@example.com", "0990000000", "0990000000", "Guayaquil", "Guayas", "Centro", "web"]]
    if import_type == ImportBatch.ImportType.INVENTORY:
        return ["sku", "nombre", "categoria", "tipo_articulo", "unidad", "precio", "costo", "estado", "publico", "controla_stock", "descripcion"], [["ACEITE-5W30", "Aceite 5W30", "Aceites", "aceite", "litro", "12.50", "8.00", "activo", "si", "si", "Aceite sintético para mantenimiento"]]
    return ["sku", "sucursal_codigo", "cantidad", "stock_minimo", "ubicacion", "referencia"], [["ACEITE-5W30", "quito-norte", "50", "10", "Bodega A", "Carga inicial"]]


def template_instructions(import_type: str) -> list[str]:
    common = [
        "No cambies los nombres de los encabezados.",
        "Puedes dejar columnas opcionales vacías.",
        "La importación valida primero y solo aplica cambios cuando confirmas el lote.",
        "Los archivos subidos quedan en almacenamiento privado, no en /media/ ni /static/.",
    ]
    if import_type == ImportBatch.ImportType.VEHICLES:
        return common + [
            "El código interno Vinova se genera automáticamente. codigo_interno solo se usa al reimportar para actualizar una unidad que ya existe.",
            "El VIN real del fabricante es opcional y nunca se inventa automáticamente. Para actualizar una importación anterior usa su codigo_interno o su VIN real.",
            "Los vehículos confirmados alimentan el módulo interno y el catálogo público si quedan como Disponible/publicar_en_catalogo=si.",
            "La sucursal se toma de sucursal_codigo/sucursal; si falta, el formulario puede aplicar una sucursal por defecto.",
            "La multimedia NO se importa por plantilla: fotos, galería, modelo 3D, videos y manuales se suben desde la ficha del vehículo.",
        ]
    if import_type == ImportBatch.ImportType.STOCK:
        return common + ["El stock siempre requiere sucursal por fila o sucursal por defecto en el formulario."]
    return common


def template_valid_values(import_type: str) -> dict[str, list[str]]:
    values = {
        "si_no": ["si", "no"],
        "sucursales": list(Branch.objects.filter(is_active=True).order_by("name").values_list("code", flat=True)),
    }
    if import_type == ImportBatch.ImportType.VEHICLES:
        values.update({"estado": list(VEHICLE_STATUS_MAP.keys())})
    elif import_type == ImportBatch.ImportType.CUSTOMERS:
        values.update({"tipo": list(CUSTOMER_TYPE_MAP.keys()), "identificacion_tipo": list(IDENTIFICATION_MAP.keys()), "estado": list(CUSTOMER_STATUS_MAP.keys())})
    elif import_type == ImportBatch.ImportType.INVENTORY:
        values.update({"tipo_articulo": list(ITEM_TYPE_MAP.keys()), "estado": list(ITEM_STATUS_MAP.keys())})
    return values


def build_template_workbook(import_type: str) -> Workbook:
    """Generate the typed import workbook, examples and validation guidance."""

    headers, example_rows = sample_template_rows(import_type)
    workbook = Workbook()
    workbook.properties.title = f"Plantilla Vinova Pro - {dict(ImportBatch.ImportType.choices).get(import_type, import_type)}"
    workbook.properties.subject = "Importación masiva validada por Vinova Pro"
    workbook.properties.creator = "Vinova Pro"

    navy = "17365D"
    corporate_blue = "2F75B5"
    required_fill = "1F4E78"
    optional_fill = "5B9BD5"
    instruction_fill = "EAF3F8"
    example_fill = "FFF2CC"
    danger_fill = "FCE4D6"
    white = "FFFFFF"
    muted_text = "5B6573"
    thin_gray = Side(style="thin", color="D9E2F3")
    border = Border(left=thin_gray, right=thin_gray, top=thin_gray, bottom=thin_gray)

    required_by_type = {
        ImportBatch.ImportType.VEHICLES: VEHICLE_REQUIRED_HEADERS,
        ImportBatch.ImportType.CUSTOMERS: {"tipo"},
        ImportBatch.ImportType.INVENTORY: {"sku", "nombre", "precio"},
        ImportBatch.ImportType.STOCK: {"sku", "cantidad"},
    }
    required_headers = required_by_type.get(import_type, set())

    ws = workbook.active
    ws.title = "datos"
    ws.sheet_view.showGridLines = False
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{get_column_letter(len(headers))}500"
    ws.row_dimensions[1].height = 34
    ws.append(headers)

    for col_idx, header in enumerate(headers, start=1):
        cell = ws.cell(row=1, column=col_idx)
        is_required = header in required_headers
        cell.fill = PatternFill("solid", fgColor=required_fill if is_required else optional_fill)
        cell.font = Font(color=white, bold=True, size=10)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border
        requirement = "OBLIGATORIO" if is_required else "OPCIONAL"
        cell.comment = Comment(
            f"Campo {requirement}. Encabezado reconocido por Vinova Pro; no cambies su nombre.",
            "Vinova Pro",
        )
        width = max(15, min(32, len(str(header)) + 5))
        if header in {"descripcion_publica", "resumen", "motor", "transmision", "seguridad", "interior", "tecnologia"}:
            width = 28
        ws.column_dimensions[get_column_letter(col_idx)].width = width

    # Área editable limpia: el ejemplo vive en una hoja separada para evitar importarlo por accidente.
    for row in range(2, 502):
        ws.row_dimensions[row].height = 21
        for col in range(1, len(headers) + 1):
            cell = ws.cell(row=row, column=col)
            cell.border = border
            cell.alignment = Alignment(vertical="top", wrap_text=True)
            cell.protection = Protection(locked=False)

    header_to_column = {header: idx + 1 for idx, header in enumerate(headers)}
    last_data_letter = get_column_letter(len(headers))
    for required_header in required_headers:
        if required_header not in header_to_column:
            continue
        letter = get_column_letter(header_to_column[required_header])
        ws.conditional_formatting.add(
            f"{letter}2:{letter}500",
            FormulaRule(
                formula=[f'AND(COUNTA($A2:${last_data_letter}2)>0,LEN(TRIM({letter}2))=0)'],
                stopIfTrue=False,
                fill=PatternFill("solid", fgColor=danger_fill),
            ),
        )

    # Formatos de datos más comunes.
    for header in ["año", "kilometraje", "cantidad", "stock_minimo"]:
        if header in header_to_column:
            letter = get_column_letter(header_to_column[header])
            ws[f"{letter}2"].number_format = "0"
            for row in range(2, 502):
                ws[f"{letter}{row}"].number_format = "0"
    for header in ["precio", "costo"]:
        if header in header_to_column:
            letter = get_column_letter(header_to_column[header])
            for row in range(2, 502):
                ws[f"{letter}{row}"].number_format = '$#,##0.00'

    # Validaciones visuales. La validación del servidor sigue siendo la fuente de verdad.
    canonical_status = {
        ImportBatch.ImportType.VEHICLES: ["Disponible", "Reservado", "Vendido", "En mantenimiento", "Oculto", "Archivado"],
        ImportBatch.ImportType.CUSTOMERS: ["prospecto", "activo", "vip", "inactivo", "archivado"],
        ImportBatch.ImportType.INVENTORY: ["activo", "inactivo", "archivado"],
    }
    if "estado" in header_to_column and import_type in canonical_status:
        dv = DataValidation(type="list", formula1='"' + ",".join(canonical_status[import_type]) + '"', allow_blank=True)
        dv.error = "Selecciona un estado de la lista."
        dv.errorTitle = "Estado no válido"
        dv.prompt = "Selecciona un valor permitido."
        dv.promptTitle = "Estado"
        ws.add_data_validation(dv)
        letter = get_column_letter(header_to_column["estado"])
        dv.add(f"{letter}2:{letter}500")

    for bool_header in ["publicar_en_catalogo", "destacado", "publico", "controla_stock"]:
        if bool_header in header_to_column:
            dv = DataValidation(type="list", formula1='"si,no"', allow_blank=True)
            dv.error = "Usa únicamente si o no."
            dv.errorTitle = "Valor no válido"
            ws.add_data_validation(dv)
            letter = get_column_letter(header_to_column[bool_header])
            dv.add(f"{letter}2:{letter}500")

    if "año" in header_to_column:
        dv = DataValidation(
            type="whole",
            operator="between",
            formula1=str(MIN_VEHICLE_YEAR),
            formula2=str(timezone.now().year + MAX_VEHICLE_YEAR_OFFSET),
            allow_blank=False,
        )
        dv.error = f"El año debe estar entre {MIN_VEHICLE_YEAR} y {timezone.now().year + MAX_VEHICLE_YEAR_OFFSET}."
        dv.errorTitle = "Año no válido"
        ws.add_data_validation(dv)
        letter = get_column_letter(header_to_column["año"])
        dv.add(f"{letter}2:{letter}500")

    if "kilometraje" in header_to_column:
        dv = DataValidation(type="whole", operator="greaterThanOrEqual", formula1="0", allow_blank=True)
        dv.error = "El kilometraje no puede ser negativo."
        ws.add_data_validation(dv)
        letter = get_column_letter(header_to_column["kilometraje"])
        dv.add(f"{letter}2:{letter}500")

    if "precio" in header_to_column:
        dv = DataValidation(type="decimal", operator="greaterThanOrEqual", formula1="0", allow_blank=True)
        dv.error = "El precio no puede ser negativo."
        ws.add_data_validation(dv)
        letter = get_column_letter(header_to_column["precio"])
        dv.add(f"{letter}2:{letter}500")

    # Hoja de instrucciones.
    instructions = workbook.create_sheet("instrucciones")
    instructions.sheet_view.showGridLines = False
    instructions.merge_cells("A1:D1")
    instructions["A1"] = f"Plantilla de importación · {dict(ImportBatch.ImportType.choices).get(import_type, import_type)}"
    instructions["A1"].fill = PatternFill("solid", fgColor=navy)
    instructions["A1"].font = Font(color=white, bold=True, size=16)
    instructions["A1"].alignment = Alignment(vertical="center")
    instructions.row_dimensions[1].height = 32
    instructions["A3"] = "Cómo usar esta plantilla"
    instructions["A3"].font = Font(color=navy, bold=True, size=12)
    for idx, line in enumerate(template_instructions(import_type), start=4):
        instructions[f"A{idx}"] = f"{idx - 3}. {line}"
        instructions[f"A{idx}"].alignment = Alignment(wrap_text=True, vertical="top")
        instructions[f"A{idx}"].fill = PatternFill("solid", fgColor=instruction_fill)
        instructions[f"A{idx}"].border = border
        instructions.row_dimensions[idx].height = 32
    instructions["A12"] = "Leyenda"
    instructions["A12"].font = Font(color=navy, bold=True)
    instructions["A13"] = "Encabezado azul oscuro"
    instructions["B13"] = "Campo obligatorio"
    instructions["A13"].fill = PatternFill("solid", fgColor=required_fill)
    instructions["A13"].font = Font(color=white, bold=True)
    instructions["A14"] = "Encabezado azul claro"
    instructions["B14"] = "Campo opcional"
    instructions["A14"].fill = PatternFill("solid", fgColor=optional_fill)
    instructions["A14"].font = Font(color=white, bold=True)
    instructions.column_dimensions["A"].width = 82
    instructions.column_dimensions["B"].width = 28
    instructions.column_dimensions["C"].width = 18
    instructions.column_dimensions["D"].width = 18

    # Ejemplo separado: no se importa accidentalmente al cargar la hoja datos.
    example = workbook.create_sheet("ejemplo")
    example.sheet_view.showGridLines = False
    example.freeze_panes = "A2"
    example.append(headers)
    for row in example_rows:
        example.append(row)
    for col_idx, header in enumerate(headers, start=1):
        cell = example.cell(row=1, column=col_idx)
        cell.fill = PatternFill("solid", fgColor=corporate_blue)
        cell.font = Font(color=white, bold=True)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        cell.border = border
        example.column_dimensions[get_column_letter(col_idx)].width = ws.column_dimensions[get_column_letter(col_idx)].width
    for row in example.iter_rows(min_row=2, max_row=max(2, example.max_row), max_col=len(headers)):
        for cell in row:
            cell.fill = PatternFill("solid", fgColor=example_fill)
            cell.border = border
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    example["A4"] = "Este contenido es solo una guía. Copia los datos necesarios a la hoja 'datos'."
    example["A4"].font = Font(color=muted_text, italic=True)

    # Sucursales activas disponibles para usar como sucursal_codigo.
    branches = workbook.create_sheet("sucursales")
    branches.sheet_view.showGridLines = False
    branches.append(["codigo", "nombre", "ciudad", "empresa"])
    for branch in Branch.objects.select_related("company").filter(is_active=True).order_by("company__commercial_name", "name"):
        branches.append([branch.code, branch.name, branch.city, branch.company.commercial_name or branch.company.legal_name])
    for cell in branches[1]:
        cell.fill = PatternFill("solid", fgColor=corporate_blue)
        cell.font = Font(color=white, bold=True)
        cell.border = border
    branches.freeze_panes = "A2"
    branches.auto_filter.ref = f"A1:D{max(2, branches.max_row)}"
    for col, width in {"A": 22, "B": 30, "C": 22, "D": 34}.items():
        branches.column_dimensions[col].width = width
    for row in branches.iter_rows(min_row=2, max_row=max(2, branches.max_row), max_col=4):
        for cell in row:
            cell.border = border

    if "sucursal_codigo" in header_to_column and branches.max_row >= 2:
        letter = get_column_letter(header_to_column["sucursal_codigo"])
        branch_range_name = DefinedName(
            "SucursalesCodigos",
            attr_text=f"'sucursales'!$A$2:$A${branches.max_row}",
        )
        workbook.defined_names.add(branch_range_name)
        dv = DataValidation(type="list", formula1="SucursalesCodigos", allow_blank=True)
        dv.error = "Selecciona un código de sucursal de la hoja sucursales."
        dv.errorTitle = "Sucursal no válida"
        ws.add_data_validation(dv)
        dv.add(f"{letter}2:{letter}500")

    values_sheet = workbook.create_sheet("valores_validos")
    values_sheet.sheet_view.showGridLines = False
    values = template_valid_values(import_type)
    max_len = max([len(v) for v in values.values()] or [0])
    keys = list(values.keys())
    values_sheet.append(keys)
    for idx in range(max_len):
        values_sheet.append([values[key][idx] if idx < len(values[key]) else "" for key in keys])
    for cell in values_sheet[1]:
        cell.fill = PatternFill("solid", fgColor=corporate_blue)
        cell.font = Font(color=white, bold=True)
        cell.border = border
    values_sheet.freeze_panes = "A2"
    for idx in range(1, len(keys) + 1):
        values_sheet.column_dimensions[get_column_letter(idx)].width = 24
    for row in values_sheet.iter_rows(min_row=2, max_row=max(2, values_sheet.max_row), max_col=max(1, len(keys))):
        for cell in row:
            cell.border = border

    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_title_rows = "1:1"
    workbook.active = 0
    return workbook
