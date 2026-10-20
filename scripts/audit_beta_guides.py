#!/usr/bin/env python3
"""ES: Audita estructura, trazabilidad y lenguaje seguro de las guías beta.

EN: Audits beta-guide structure, traceability, and safe language.
"""

from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
GUIDES_DIR = ROOT / "docs" / "testeo-beta"
CASE_RE = re.compile(r"^\|\s*([A-Z]+-\d{3})\s*\|", re.MULTILINE)
FULL_ID_RE = re.compile(r"(?<!\d)\d{10}(?!\d)")


def audit() -> dict[str, object]:
    """ES: Verifica campos, IDs, pasos, estados y datos sensibles evidentes.

    EN: Verifies fields, IDs, steps, statuses, and obvious sensitive data.
    """

    guides = sorted(GUIDES_DIR.glob("testeo-*.md"))
    case_owners: dict[str, str] = {}
    issues: list[str] = []
    role_or_module = 0
    for path in guides:
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT).as_posix()
        is_case_guide = path.name.startswith(("testeo-rol-", "testeo-modulo-"))
        if is_case_guide:
            role_or_module += 1
            for heading in ("## Objetivo", "## Requisitos previos", "## Casos", "## Checklist"):
                if heading not in text:
                    issues.append(f"{relative}: falta {heading}")
            for column in ("Pasos numerados", "Resultado esperado observable", "Resultado obtenido", "Estado", "Evidencia", "Observaciones"):
                if column not in text:
                    issues.append(f"{relative}: falta columna {column}")
        for line in text.splitlines():
            match = re.match(r"^\|\s*([A-Z]+-\d{3})\s*\|", line)
            if not match:
                continue
            case_id = match.group(1)
            if case_id in case_owners:
                issues.append(f"{relative}: ID duplicado {case_id} (también en {case_owners[case_id]})")
            else:
                case_owners[case_id] = relative
            if line.count("|") < 10:
                issues.append(f"{relative}: fila incompleta {case_id}")
            if not all(step in line for step in ("1.", "2.")):
                issues.append(f"{relative}: pasos insuficientes {case_id}")
            if "|  | pendiente |" not in line:
                issues.append(f"{relative}: estado maestro distinto de pendiente en {case_id}")
            if text.count(f"`{case_id}`") < 1:
                issues.append(f"{relative}: {case_id} no aparece en checklist")
        lower_text = text.lower()
        prose = re.sub(r"`[^`]+`", "", lower_text)
        if "serializer" in prose:
            issues.append(f"{relative}: jerga serializer no explicada")
        if "ownership" in prose and "también llamado *ownership*" not in prose:
            issues.append(f"{relative}: jerga ownership no explicada")
        if "rbac" in prose and "rbac significa" not in prose and "matriz-rbac.md" not in prose:
            issues.append(f"{relative}: sigla RBAC no explicada")
        if FULL_ID_RE.search(text):
            issues.append(f"{relative}: posible identificador personal de 10 dígitos")
    return {
        "guide_files": len(guides),
        "role_or_module_guides": role_or_module,
        "manual_cases": len(case_owners),
        "duplicate_or_missing_issues": issues,
    }


def main() -> int:
    """ES: Imprime un reporte JSON y falla cuando existe una desviación.

    EN: Prints a JSON report and fails when a deviation exists.
    """

    report = audit()
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 1 if report["duplicate_or_missing_issues"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
