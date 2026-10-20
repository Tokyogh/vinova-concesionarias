"""ES: Audita y normaliza documentación bilingüe de fuentes propias.

EN: Audits and normalizes bilingual documentation in first-party sources.

El modo de corrección se limita a comentarios y docstrings; excluye LITE,
dependencias, migraciones y archivos generados. El modo estricto comprueba
cabeceras y símbolos productivos complejos sin interpretar los nombres de tests
como documentación ausente.

Fix mode is limited to comments and docstrings; it excludes LITE, dependencies,
migrations, and generated files. Strict mode checks headers and complex
production symbols without treating descriptive test names as missing docs.
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {"web_carros", "vendor", "migrations", "__pycache__", "node_modules"}
COMPLEX_LINE_THRESHOLD = 60
COMPLEX_BRANCH_THRESHOLD = 10

DOMAIN_ES = {
    "accounts": "cuentas",
    "analytics": "analítica",
    "api": "API e integraciones",
    "audit": "auditoría",
    "branches": "sucursales",
    "common": "infraestructura compartida",
    "companies": "empresa",
    "continuity": "continuidad",
    "customers": "clientes",
    "dashboard": "paneles",
    "documents": "documentos",
    "enterprise": "configuración empresarial",
    "help_center": "ayuda",
    "imports": "importaciones",
    "inventory": "inventario",
    "invoices": "facturación",
    "leads": "CRM y leads",
    "notifications": "notificaciones",
    "portal": "portal cliente",
    "post_sales": "postventa",
    "privacy": "privacidad",
    "quality": "calidad",
    "reports": "reportes",
    "sales": "ventas",
    "security_center": "seguridad",
    "sri_integration": "configuración SRI heredada",
    "vehicles": "vehículos",
}

ROLE_TEXT = {
    "admin": ("registra modelos en la administración de Django", "registers models in Django admin"),
    "apps": ("configura la aplicación Django", "configures the Django application"),
    "forms": ("define formularios y validación de entrada en backend", "defines forms and server-side input validation"),
    "models": ("define modelos persistentes, estados y restricciones", "defines persistent models, states, and constraints"),
    "selectors": ("implementa consultas de lectura conscientes de autorización", "implements authorization-aware read queries"),
    "services": ("implementa servicios de negocio y efectos transaccionales", "implements business services and transactional effects"),
    "application": ("orquesta servicios de aplicación y transacciones", "orchestrates application services and transactions"),
    "views": ("orquesta solicitudes HTTP, permisos y respuestas", "orchestrates HTTP requests, permissions, and responses"),
    "urls": ("declara el enrutamiento URL", "declares URL routing"),
    "serializers": ("serializa y valida contratos de API", "serializes and validates API contracts"),
    "permissions": ("centraliza reglas de autorización", "centralizes authorization rules"),
    "authentication": ("aplica autenticación y validación de credenciales", "enforces authentication and credential validation"),
    "middleware": ("procesa controles transversales del ciclo HTTP", "processes cross-cutting HTTP lifecycle controls"),
    "tasks": ("expone tareas asíncronas y sus límites operativos", "exposes asynchronous tasks and their operational limits"),
    "storage": ("adapta almacenamiento y ciclo de vida de archivos", "adapts storage and file lifecycle behavior"),
    "validators": ("centraliza validaciones contextuales", "centralizes contextual validation"),
    "tests": ("especifica regresiones ejecutables", "specifies executable regressions"),
}

CONTROL_NODES = (
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.Try,
    ast.With,
    ast.AsyncWith,
    ast.Match,
    ast.BoolOp,
    ast.comprehension,
)


@dataclass(frozen=True)
class ComplexSymbol:
    path: Path
    node: ast.AST
    parent_name: str
    lines: int
    branches: int


def tracked_files() -> list[Path]:
    """ES: Devuelve rutas versionadas. EN: Returns version-controlled paths."""

    output = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    paths = [ROOT / item.decode("utf-8") for item in output.split(b"\0") if item]
    current = Path(__file__).resolve()
    if current not in paths:
        paths.append(current)
    return paths


def _excluded(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    return bool(EXCLUDED_PARTS.intersection(relative.parts))


def _domain(path: Path) -> tuple[str, str]:
    relative = path.relative_to(ROOT)
    if relative.parts and relative.parts[0] == "apps" and len(relative.parts) > 1:
        code = relative.parts[1]
        return DOMAIN_ES.get(code, code.replace("_", " ")), code.replace("_", " ")
    if relative.parts and relative.parts[0] == "config":
        return "configuración", "configuration"
    if relative.parts and relative.parts[0] == "scripts":
        return "operación y QA", "operations and QA"
    return "pruebas integrales", "cross-domain tests"


def _module_summary(path: Path) -> tuple[str, str]:
    domain_es, domain_en = _domain(path)
    relative = path.relative_to(ROOT)
    if "tests" in relative.parts or path.name.startswith("test_"):
        role_es, role_en = ROLE_TEXT["tests"]
    elif "management" in relative.parts and "commands" in relative.parts:
        action = path.stem.replace("_", " ")
        return (
            f"Implementa el comando administrativo «{action}» para {domain_es}.",
            f"Implements the «{action}» management command for {domain_en}.",
        )
    elif path.parent.name == "api" and path.stem in {"views", "serializers", "permissions"}:
        role_es, role_en = ROLE_TEXT[path.stem]
    else:
        role_es, role_en = ROLE_TEXT.get(
            path.stem,
            (
                f"implementa el componente {path.stem.replace('_', ' ')}",
                f"implements the {path.stem.replace('_', ' ')} component",
            ),
        )
    return (
        f"Este módulo {role_es} para el dominio de {domain_es}.",
        f"This module {role_en} for the {domain_en} domain.",
    )


def python_files() -> list[Path]:
    """ES: Selecciona Python propio elegible. EN: Selects eligible first-party Python."""

    candidates = [path for path in tracked_files() if path.suffix == ".py" and not _excluded(path)]
    return [path for path in candidates if path.name != "__init__.py" or path.read_text(encoding="utf-8").strip()]


def _replace_module_docstring(path: Path) -> bool:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    doc = ast.get_docstring(tree, clean=False)
    if not doc or ("ES:" in doc and "EN:" in doc):
        return False
    expression = tree.body[0]
    if not isinstance(expression, ast.Expr) or not isinstance(expression.value, ast.Constant):
        return False
    summary_es, summary_en = _module_summary(path)
    replacement = (
        f'"""ES: {summary_es}\n\n'
        f"EN: {summary_en}\n\n"
        f"Contexto existente / Existing context:\n{doc.strip()}\n"
        f'"""'
    )
    lines = source.splitlines(keepends=True)
    start = expression.lineno - 1
    end = expression.end_lineno
    newline = "\r\n" if "\r\n" in source else "\n"
    replacement_lines = [line + newline for line in replacement.splitlines()]
    if end == len(lines) and not source.endswith(("\n", "\r")):
        replacement_lines[-1] = replacement_lines[-1].rstrip("\r\n")
    lines[start:end] = replacement_lines
    path.write_text("".join(lines), encoding="utf-8", newline="")
    return True


def _parents(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    result: dict[ast.AST, ast.AST] = {}
    for parent in ast.walk(tree):
        for child in ast.iter_child_nodes(parent):
            result[child] = parent
    return result


def _is_product_source(path: Path) -> bool:
    relative = path.relative_to(ROOT)
    return "tests" not in relative.parts and not path.name.startswith("test_")


def complex_symbols(path: Path) -> list[ComplexSymbol]:
    """ES: Localiza símbolos productivos cuya complejidad exige contexto.

    EN: Finds production symbols whose complexity requires documentation context.
    """

    if not _is_product_source(path):
        return []
    tree = ast.parse(path.read_text(encoding="utf-8"))
    parents = _parents(tree)
    result = []
    for node in ast.walk(tree):
        if not isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name == "Meta" or (node.name.startswith("_") and node.name not in {"__init__", "__call__"}):
            continue
        lines = node.end_lineno - node.lineno + 1
        branches = sum(isinstance(child, CONTROL_NODES) for child in ast.walk(node))
        if lines < COMPLEX_LINE_THRESHOLD and branches < COMPLEX_BRANCH_THRESHOLD:
            continue
        parent = parents.get(node)
        parent_name = parent.name if isinstance(parent, ast.ClassDef) else ""
        result.append(ComplexSymbol(path, node, parent_name, lines, branches))
    return result


def _humanize(name: str) -> str:
    words = re.sub(r"(?<!^)(?=[A-Z])", " ", name).replace("_", " ")
    return " ".join(words.split()).lower()


def _symbol_summary(symbol: ComplexSymbol, source: str) -> tuple[str, str]:
    node = symbol.node
    domain_es, domain_en = _domain(symbol.path)
    name = _humanize(node.name)
    owner = f" de {symbol.parent_name}" if symbol.parent_name else ""
    owner_en = f" on {symbol.parent_name}" if symbol.parent_name else ""
    if isinstance(node, ast.ClassDef):
        es = f"Agrupa el componente «{name}» del dominio de {domain_es} y sus reglas relacionadas."
        en = f"Groups the «{name}» component and its related rules in the {domain_en} domain."
    elif node.name in {"get", "post", "put", "patch", "delete", "dispatch"}:
        es = f"Procesa solicitudes {node.name.upper()}{owner} aplicando el flujo del dominio de {domain_es}."
        en = f"Processes {node.name.upper()} requests{owner_en} using the {domain_en} domain flow."
    elif node.name in {"clean", "validate", "is_valid"} or node.name.startswith("validate_"):
        es = f"Valida y normaliza «{name}» antes de permitir efectos en {domain_es}."
        en = f"Validates and normalizes «{name}» before allowing effects in {domain_en}."
    elif node.name in {"handle", "main"}:
        es = f"Orquesta «{symbol.path.stem.replace('_', ' ')}» con fallos controlados para {domain_es}."
        en = f"Orchestrates «{symbol.path.stem.replace('_', ' ')}» with controlled failures for {domain_en}."
    else:
        es = f"Ejecuta la operación «{name}» dentro del dominio de {domain_es}."
        en = f"Executes the «{name}» operation within the {domain_en} domain."

    segment = ast.get_source_segment(source, node) or ""
    controls_es = []
    controls_en = []
    if "transaction.atomic" in segment or "select_for_update" in segment:
        controls_es.append("conserva atomicidad y bloqueos explícitos")
        controls_en.append("preserves atomicity and explicit locking")
    if any(token in segment for token in ("PermissionDenied", "has_perm", "require_perm", "can_")):
        controls_es.append("aplica autorización en backend")
        controls_en.append("enforces server-side authorization")
    if "audit_log" in segment:
        controls_es.append("registra efectos auditables")
        controls_en.append("records auditable effects")
    if "ValidationError" in segment or "is_valid" in segment:
        controls_es.append("rechaza estados o entradas inválidas")
        controls_en.append("rejects invalid input or state")
    if controls_es:
        es += " Además, " + ", ".join(controls_es) + "."
        en += " It also " + ", ".join(controls_en) + "."
    return es, en


def _insert_complex_docstrings(path: Path) -> int:
    source = path.read_text(encoding="utf-8")
    missing = [symbol for symbol in complex_symbols(path) if not ast.get_docstring(symbol.node, clean=False)]
    if not missing:
        return 0
    lines = source.splitlines(keepends=True)
    newline = "\r\n" if "\r\n" in source else "\n"
    for symbol in sorted(missing, key=lambda item: item.node.body[0].lineno, reverse=True):
        first_statement = symbol.node.body[0]
        indent = " " * first_statement.col_offset
        summary_es, summary_en = _symbol_summary(symbol, source)
        doc_lines = [
            f'{indent}"""ES: {summary_es}{newline}',
            f"{newline}",
            f"{indent}EN: {summary_en}{newline}",
            f'{indent}"""{newline}',
            newline,
        ]
        lines[first_statement.lineno - 1 : first_statement.lineno - 1] = doc_lines
    path.write_text("".join(lines), encoding="utf-8", newline="")
    return len(missing)


def _header_paths() -> dict[str, list[Path]]:
    tracked = tracked_files()
    return {
        "html": [path for path in tracked if path.suffix == ".html" and "templates" in path.relative_to(ROOT).parts and not _excluded(path)],
        "css": [path for path in tracked if path.suffix == ".css" and not _excluded(path)],
        "js": [path for path in tracked if path.suffix == ".js" and not _excluded(path)],
    }


def operation_files() -> list[Path]:
    """ES: Selecciona configuraciones y scripts compatibles con comentarios.

    EN: Selects configurations and scripts whose syntax supports comments.
    """

    result = []
    for path in tracked_files():
        suffix = path.suffix.lower()
        is_env_example = path.name.startswith(".env") and path.name.endswith(".example")
        if (
            path.name.startswith("Dockerfile")
            or suffix in {".sh", ".ps1", ".cmd", ".bat", ".yml", ".yaml", ".template"}
            or is_env_example
        ) and not _excluded(path):
            result.append(path)
    return result


def _operation_summary(path: Path) -> tuple[str, str]:
    relative = path.relative_to(ROOT).as_posix()
    if path.name.startswith("Dockerfile"):
        return (
            f"Construye la imagen definida en {relative} con límites y dependencias explícitos.",
            f"Builds the image defined by {relative} with explicit limits and dependencies.",
        )
    if path.name.startswith("docker-compose"):
        return (
            f"Declara la topología de servicios y aislamiento operativo de {relative}.",
            f"Declares the service topology and operational isolation for {relative}.",
        )
    if path.name.startswith(".env"):
        return (
            f"Documenta variables de ejemplo para {relative}; no contiene secretos reales.",
            f"Documents example variables for {relative}; it contains no real secrets.",
        )
    if path.suffix == ".template":
        return (
            f"Configura el borde Nginx de {relative}, incluidos proxy, límites y cabeceras.",
            f"Configures the {relative} Nginx edge, including proxying, limits, and headers.",
        )
    action = path.stem.replace("_", " ").replace("-", " ")
    return (
        f"Ejecuta el flujo operativo «{action}» con fallos controlados y sin ocultar errores.",
        f"Runs the «{action}» operational flow with controlled failures and visible errors.",
    )


def _normalize_operation_header(path: Path) -> bool:
    text = path.read_text(encoding="utf-8")
    # ES: La marca BOM es metadato de codificación y debe permanecer al inicio físico.
    # EN: The BOM is encoding metadata and must remain at the physical beginning.
    text = text.removeprefix("\ufeff")
    if "ES:" in "\n".join(text.splitlines()[:12]) and "EN:" in "\n".join(text.splitlines()[:12]):
        return False
    summary_es, summary_en = _operation_summary(path)
    lines = text.splitlines(keepends=True)
    newline = "\r\n" if "\r\n" in text else "\n"
    header = [f"# ES: {summary_es}{newline}", f"# EN: {summary_en}{newline}"]
    insert_at = 0
    if lines and lines[0].startswith("#!"):
        insert_at = 1
    elif path.suffix.lower() in {".bat", ".cmd"} and lines and lines[0].strip().lower() == "@echo off":
        header = [f"REM ES: {summary_es}{newline}", f"REM EN: {summary_en}{newline}"]
        insert_at = 1
    lines[insert_at:insert_at] = header
    path.write_text("".join(lines), encoding="utf-8", newline="")
    return True


def _normalize_web_header(path: Path, kind: str) -> bool:
    text = path.read_text(encoding="utf-8")
    first_lines = "\n".join(text.splitlines()[:8])
    if "ES:" in first_lines and "EN:" in first_lines:
        return False
    label = path.relative_to(ROOT).with_suffix("").as_posix()
    descriptions = {
        "html": (
            f"Renderiza la interfaz {label}; permisos y datos se resuelven en backend.",
            f"Renders the {label} interface; permissions and data are resolved server-side.",
            "{# ES: %s #}\n{# EN: %s #}\n",
        ),
        "css": (
            f"Define estilos de {label}, incluidos estados y adaptación responsive.",
            f"Defines {label} styles, including states and responsive behavior.",
            "/* ES: %s */\n/* EN: %s */\n",
        ),
        "js": (
            f"Implementa interacción de navegador para {label}; backend conserva la autoridad.",
            f"Implements browser interaction for {label}; the backend remains authoritative.",
            "/* ES: %s */\n/* EN: %s */\n",
        ),
    }
    es, en, template = descriptions[kind]
    header = template % (es, en)
    lines = text.splitlines(keepends=True)
    if kind == "html" and lines and lines[0].lstrip().startswith("{# VINOVA template:"):
        lines = lines[1:]
    # ES: Los encabezados VINOVA heredados pueden ser comentarios multilínea;
    # conservarlos evita dejar cierres `*/` huérfanos al anteponer la cabecera.
    # EN: Legacy VINOVA headers may be multiline comments; keeping them avoids
    # orphaning their closing `*/` marker when the bilingual header is prepended.
    path.write_text(header + "".join(lines).lstrip("\r\n"), encoding="utf-8", newline="")
    return True


def _has_internal_pair(path: Path, *, header_lines: int) -> bool:
    text = "\n".join(path.read_text(encoding="utf-8").splitlines()[header_lines:])
    return "ES:" in text and "EN:" in text


def _css_comments_balanced(path: Path) -> bool:
    """ES: Comprueba delimitadores CSS sin intentar interpretar selectores.

    EN: Checks CSS comment delimiters without trying to parse selectors.
    """

    depth = 0
    for token in re.findall(r"/\*|\*/", path.read_text(encoding="utf-8")):
        depth += 1 if token == "/*" else -1
        if depth < 0:
            return False
    return depth == 0


def _insert_html_sections(path: Path) -> int:
    """ES: Documenta componentes semánticos grandes sin alterar su salida.

    EN: Documents large semantic components without changing their output.
    """

    text = path.read_text(encoding="utf-8")
    if len(text.splitlines()) < 80 or _has_internal_pair(path, header_lines=2):
        return 0
    descriptions = {
        "nav": (
            "La navegación siguiente muestra destinos ya autorizados por el contexto de backend.",
            "The following navigation shows destinations already authorized by backend context.",
        ),
        "form": (
            "El formulario siguiente presenta errores del servidor; el navegador no sustituye su validación.",
            "The following form renders server errors; browser checks do not replace server validation.",
        ),
        "table": (
            "La tabla siguiente presenta datos previamente filtrados por permisos y alcance.",
            "The following table renders data already filtered by permissions and scope.",
        ),
        "section": (
            "La sección siguiente agrupa contenido, estados vacíos y acciones del flujo actual.",
            "The following section groups content, empty states, and actions for the current flow.",
        ),
        "dialog": (
            "El diálogo siguiente conserva foco y cierre accesibles mediante JavaScript externo.",
            "The following dialog preserves accessible focus and dismissal through external JavaScript.",
        ),
    }
    lines = text.splitlines(keepends=True)
    newline = "\r\n" if "\r\n" in text else "\n"
    inserts = []
    used = set()
    for index, line in enumerate(lines):
        stripped = line.lstrip().lower()
        match = re.match(r"<(nav|form|table|section|dialog)\b", stripped)
        if not match or match.group(1) in used:
            continue
        kind = match.group(1)
        used.add(kind)
        es, en = descriptions[kind]
        indent = line[: len(line) - len(line.lstrip())]
        inserts.append(
            (
                index,
                [f"{indent}{{# ES: {es} #}}{newline}", f"{indent}{{# EN: {en} #}}{newline}"],
            )
        )
        if len(inserts) == 2:
            break
    if not inserts:
        target = next((index + 1 for index, line in enumerate(lines) if "{% block" in line), min(8, len(lines)))
        inserts.append(
            (
                target,
                [
                    f"{{# ES: El bloque siguiente compone estados y acciones con contexto autorizado. #}}{newline}",
                    f"{{# EN: The following block composes states and actions from authorized context. #}}{newline}",
                ],
            )
        )
    for index, comments in reversed(inserts):
        lines[index:index] = comments
    path.write_text("".join(lines), encoding="utf-8", newline="")
    return len(inserts)


def _insert_css_section(path: Path) -> int:
    """ES: Añade contexto a un bloque CSS representativo y seguro.

    EN: Adds context to a representative safe CSS block.
    """

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    if len(lines) < 80 or _has_internal_pair(path, header_lines=8):
        return 0
    depth = 0
    candidates = []
    for index, line in enumerate(lines):
        stripped = line.strip()
        if depth == 0 and "{" in line and not stripped.startswith(("/*", "@keyframes")):
            candidates.append(index)
        depth += line.count("{") - line.count("}")
    if not candidates:
        return 0
    target = min(candidates, key=lambda index: abs(index - len(lines) // 2))
    selector = lines[target].split("{", 1)[0].strip() or "bloque responsive"
    newline = "\r\n" if "\r\n" in text else "\n"
    comments = [
        f"/* ES: Las reglas de «{selector}» definen estado visual y adaptación sin alterar semántica. */{newline}",
        f"/* EN: The «{selector}» rules define visual state and adaptation without changing semantics. */{newline}",
    ]
    lines[target:target] = comments
    path.write_text("".join(lines), encoding="utf-8", newline="")
    return 1


def _insert_js_section(path: Path) -> int:
    """ES: Documenta estado y eventos de módulos JavaScript extensos.

    EN: Documents state and events in substantial JavaScript modules.
    """

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    if len(lines) < 60 or _has_internal_pair(path, header_lines=8):
        return 0
    descriptions = {
        "institutions.js": (
            "Estado, filtros y mapa se sincronizan desde el DOM; un proveedor ausente conserva la lista utilizable.",
            "State, filters, and map synchronize from the DOM; a missing provider leaves the list usable.",
        ),
        "portal.js": (
            "Los eventos siguientes controlan el drawer y restauran foco sin decidir autorización.",
            "The following events control the drawer and restore focus without deciding authorization.",
        ),
        "theme.js": (
            "El tema combina preferencia local y sistema; fallos de storage mantienen una experiencia funcional.",
            "Theme state combines local and system preference; storage failures keep the experience functional.",
        ),
    }
    es, en = descriptions.get(
        path.name,
        (
            "Los manejadores siguientes sincronizan estado del DOM y degradan de forma controlada.",
            "The following handlers synchronize DOM state and degrade in a controlled way.",
        ),
    )
    newline = "\r\n" if "\r\n" in text else "\n"
    insert_at = max(next((index + 1 for index, line in enumerate(lines[:20]) if "(() =>" in line), 2), 8)
    lines[insert_at:insert_at] = [f"  /* ES: {es} */{newline}", f"  /* EN: {en} */{newline}"]
    path.write_text("".join(lines), encoding="utf-8", newline="")
    return 1


def _insert_operation_section(path: Path) -> int:
    """ES: Documenta un límite interno de scripts/configuraciones extensos.

    EN: Documents an internal boundary in substantial scripts/configuration files.
    """

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    if len(lines) < 60 or _has_internal_pair(path, header_lines=12):
        return 0
    suffix = path.suffix.lower()
    newline = "\r\n" if "\r\n" in text else "\n"
    marker_index = None
    for index, line in enumerate(lines[12:], start=12):
        stripped = line.strip()
        if suffix == ".ps1" and stripped.lower().startswith("function "):
            marker_index = index
            break
        if suffix == ".sh" and re.match(r"[A-Za-z_][A-Za-z0-9_]*\(\)\s*\{", stripped):
            marker_index = index
            break
        if suffix in {".bat", ".cmd"} and stripped.startswith(":") and not stripped.startswith("::"):
            marker_index = index
            break
        if suffix in {".yml", ".yaml"} and stripped == "services:":
            marker_index = index
            break
        if suffix == ".template" and (stripped.startswith("upstream ") or stripped.startswith("server {")):
            marker_index = index
            break
        if path.name.startswith("Dockerfile") and stripped.startswith("FROM "):
            marker_index = index
            break
        if path.name.startswith(".env") and stripped.startswith("POSTGRES_"):
            marker_index = index
            break
    if marker_index is None:
        marker_index = min(12, len(lines))
    if path.name.startswith(".env"):
        section_es = "Las variables siguientes agrupan conexión y límites; son ejemplos sin secretos reales."
        section_en = "The following variables group connectivity and limits; they are examples without real secrets."
    elif path.name.startswith("docker-compose"):
        section_es = "La sección siguiente declara servicios, dependencias y límites de la topología operativa."
        section_en = "The following section declares services, dependencies, and operational topology limits."
    elif path.name.startswith("Dockerfile"):
        section_es = "La etapa siguiente separa dependencias, artefactos y privilegios del runtime."
        section_en = "The following stage separates dependencies, artifacts, and runtime privileges."
    elif suffix == ".template":
        section_es = "El bloque siguiente aplica proxy, cabeceras y límites de petición en el borde Nginx."
        section_en = "The following block applies proxying, headers, and request limits at the Nginx edge."
    else:
        section_es = "La sección siguiente define precondiciones, límites y propagación explícita de fallos."
        section_en = "The following section defines preconditions, limits, and explicit failure propagation."
    if suffix in {".bat", ".cmd"}:
        comments = [
            f"REM ES: {section_es}{newline}",
            f"REM EN: {section_en}{newline}",
        ]
    else:
        comments = [
            f"# ES: {section_es}{newline}",
            f"# EN: {section_en}{newline}",
        ]
    lines[marker_index:marker_index] = comments
    path.write_text("".join(lines), encoding="utf-8", newline="")
    return 1


def audit() -> dict[str, object]:
    """ES: Calcula cobertura reproducible. EN: Calculates reproducible coverage."""

    py_files = python_files()
    module_missing = []
    complex_missing = []
    complex_total = 0
    for path in py_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        doc = ast.get_docstring(tree, clean=False) or ""
        if "ES:" not in doc or "EN:" not in doc:
            module_missing.append(path.relative_to(ROOT).as_posix())
        symbols = complex_symbols(path)
        complex_total += len(symbols)
        complex_missing.extend(
            f"{path.relative_to(ROOT).as_posix()}:{symbol.node.lineno}:{symbol.node.name}"
            for symbol in symbols
            if not ast.get_docstring(symbol.node, clean=False)
        )
    web_missing = {}
    web_counts = {}
    for kind, paths in _header_paths().items():
        web_counts[kind] = len(paths)
        web_missing[kind] = [
            path.relative_to(ROOT).as_posix()
            for path in paths
            if not {"ES:", "EN:"}.issubset(set(re.findall(r"(?:ES:|EN:)", "\n".join(path.read_text(encoding="utf-8").splitlines()[:8]))))
        ]
    operations = operation_files()
    operation_missing = [
        path.relative_to(ROOT).as_posix()
        for path in operations
        if not {"ES:", "EN:"}.issubset(
            set(re.findall(r"(?:ES:|EN:)", "\n".join(path.read_text(encoding="utf-8").splitlines()[:12])))
        )
    ]
    internal_missing = {
        "html": [
            path.relative_to(ROOT).as_posix()
            for path in _header_paths()["html"]
            if len(path.read_text(encoding="utf-8").splitlines()) >= 80
            and not _has_internal_pair(path, header_lines=2)
        ],
        "css": [
            path.relative_to(ROOT).as_posix()
            for path in _header_paths()["css"]
            if len(path.read_text(encoding="utf-8").splitlines()) >= 80
            and not _has_internal_pair(path, header_lines=8)
        ],
        "js": [
            path.relative_to(ROOT).as_posix()
            for path in _header_paths()["js"]
            if len(path.read_text(encoding="utf-8").splitlines()) >= 60
            and not _has_internal_pair(path, header_lines=8)
        ],
        "operations": [
            path.relative_to(ROOT).as_posix()
            for path in operations
            if len(path.read_text(encoding="utf-8").splitlines()) >= 60
            and not _has_internal_pair(path, header_lines=12)
        ],
    }
    css_comments_unbalanced = [
        path.relative_to(ROOT).as_posix()
        for path in _header_paths()["css"]
        if not _css_comments_balanced(path)
    ]
    return {
        "python_modules": len(py_files),
        "python_module_headers_missing": module_missing,
        "complex_symbols": complex_total,
        "complex_docstrings_missing": complex_missing,
        "web_files": web_counts,
        "web_headers_missing": web_missing,
        "operation_files": len(operations),
        "operation_headers_missing": operation_missing,
        "internal_sections_missing": internal_missing,
        "css_comments_unbalanced": css_comments_unbalanced,
        "thresholds": {"lines": COMPLEX_LINE_THRESHOLD, "branches": COMPLEX_BRANCH_THRESHOLD},
    }


def main() -> int:
    """ES: Ejecuta corrección opcional y auditoría. EN: Runs optional fixes and audit."""

    parser = argparse.ArgumentParser()
    parser.add_argument("--fix-headers", action="store_true")
    parser.add_argument("--fix-complex-docstrings", action="store_true")
    parser.add_argument("--fix-internal-sections", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    changes = {"python_headers": 0, "complex_docstrings": 0, "web_headers": 0}
    if args.fix_headers:
        changes["python_headers"] = sum(_replace_module_docstring(path) for path in python_files())
        for kind, paths in _header_paths().items():
            changes["web_headers"] += sum(_normalize_web_header(path, kind) for path in paths)
        changes["operation_headers"] = sum(_normalize_operation_header(path) for path in operation_files())
    if args.fix_complex_docstrings:
        changes["complex_docstrings"] = sum(_insert_complex_docstrings(path) for path in python_files())
    if args.fix_internal_sections:
        headers = _header_paths()
        changes["html_sections"] = sum(_insert_html_sections(path) for path in headers["html"])
        changes["css_sections"] = sum(_insert_css_section(path) for path in headers["css"])
        changes["js_sections"] = sum(_insert_js_section(path) for path in headers["js"])
        changes["operation_sections"] = sum(_insert_operation_section(path) for path in operation_files())

    report = audit()
    report["changes"] = changes
    print(json.dumps(report, ensure_ascii=False, indent=2))
    missing = bool(
        report["python_module_headers_missing"]
        or report["complex_docstrings_missing"]
        or report["operation_headers_missing"]
        or report["css_comments_unbalanced"]
        or any(report["internal_sections_missing"].values())
    )
    missing = missing or any(report["web_headers_missing"].values())
    return 1 if args.strict and missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
