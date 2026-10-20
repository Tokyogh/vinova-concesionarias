"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for evidence in the deployment_smoke helpers domain.
"""

from __future__ import annotations

import html
import json
import zipfile
from pathlib import Path
from xml.etree.ElementTree import Element, ElementTree, SubElement

from tests.deployment_smoke.helpers.models import RunState


def write_junit(state: RunState) -> Path:
    summary = state.summary()
    suite = Element(
        "testsuite",
        name="vinova-deployment-smoke",
        tests=str(len(state.checks)),
        failures=str(summary["counts"]["failed"]),
        skipped=str(summary["counts"]["skipped"]),
        time=str(summary["duration_seconds"]),
    )
    for check in state.checks:
        case = SubElement(
            suite,
            "testcase",
            classname=f"deployment_smoke.{check.scenario}",
            name=check.code,
            time=str(check.duration_seconds),
        )
        if check.status == "failed":
            failure = SubElement(case, "failure", message=check.message)
            failure.text = json.dumps(check.details, ensure_ascii=False)
        elif check.status == "skipped":
            SubElement(case, "skipped", message=check.message)
        elif check.status == "warning":
            output = SubElement(case, "system-out")
            output.text = f"WARNING: {check.message}"
    path = state.output_dir / "junit.xml"
    ElementTree(suite).write(path, encoding="utf-8", xml_declaration=True)
    return path



def _role_matrix_html(state: RunState) -> str:
    matrix = state.metadata.get("role_matrix")
    if not isinstance(matrix, dict) or not matrix:
        return ""
    role_rows = []
    for role, details in matrix.items():
        if role == "inactive":
            role_rows.append(
                f"<tr><td><strong>{html.escape(role)}</strong></td><td colspan='5'>"
                f"{'BLOQUEADO' if details.get('login_blocked') else 'REVISAR'}</td></tr>"
            )
            continue
        cells = details.get("cells", []) if isinstance(details, dict) else []
        allowed = sum(cell.get("actual") == "PERMITIDO" for cell in cells)
        blocked = sum(cell.get("actual") == "BLOQUEADO" for cell in cells)
        mismatches = sum(not cell.get("matches", False) for cell in cells)
        role_rows.append(
            "<tr>"
            f"<td><strong>{html.escape(role)}</strong></td>"
            f"<td>{allowed}</td><td>{blocked}</td><td>{len(cells)}</td>"
            f"<td>{mismatches}</td><td>{html.escape(str(details.get('dashboard_expected', '—')))}</td>"
            "</tr>"
        )
    detail_rows = []
    for role, details in matrix.items():
        if role == "inactive" or not isinstance(details, dict):
            continue
        for cell in details.get("cells", []):
            status = "passed" if cell.get("matches") else "failed"
            detail_rows.append(
                "<tr>"
                f"<td>{html.escape(role)}</td><td>{html.escape(str(cell.get('label', '')))}</td>"
                f"<td><code>{html.escape(str(cell.get('path', '')))}</code></td>"
                f"<td>{html.escape(str(cell.get('expected', '')))}</td>"
                f"<td>{html.escape(str(cell.get('actual', '')))}</td>"
                f"<td>{html.escape(str(cell.get('status_code', '')))}</td>"
                f"<td><span class='status {status}'>{'OK' if status == 'passed' else 'DIFERENCIA'}</span></td>"
                "</tr>"
            )
    return (
        "<h2>Matriz de autorización por rol</h2>"
        "<table><thead><tr><th>Rol</th><th>Permitidos</th><th>Bloqueados</th><th>Pruebas</th>"
        "<th>Diferencias</th><th>Dashboard esperado</th></tr></thead><tbody>"
        + "".join(role_rows)
        + "</tbody></table>"
        "<h3>Detalle de capacidades</h3>"
        "<table><thead><tr><th>Rol</th><th>Capacidad</th><th>Ruta</th><th>Esperado</th>"
        "<th>Real</th><th>HTTP</th><th>Resultado</th></tr></thead><tbody>"
        + "".join(detail_rows)
        + "</tbody></table>"
    )

def write_html(state: RunState) -> Path:
    report = state.summary()
    rows = []
    for check in state.checks:
        evidence = "<br>".join(html.escape(item) for item in check.evidence) or "—"
        rows.append(
            "<tr>"
            f"<td>{html.escape(check.scenario)}</td>"
            f"<td><code>{html.escape(check.code)}</code><br>{html.escape(check.title)}</td>"
            f"<td><span class='status {html.escape(check.status)}'>{html.escape(check.status.upper())}</span></td>"
            f"<td>{html.escape(check.message)}</td>"
            f"<td>{evidence}</td>"
            "</tr>"
        )
    captures = []
    for image in sorted((state.output_dir / "screenshots").glob("*.png")) if (state.output_dir / "screenshots").exists() else []:
        relative = image.relative_to(state.output_dir).as_posix()
        captures.append(f"<figure><img src='{html.escape(relative)}' alt='Evidencia'><figcaption>{html.escape(image.name)}</figcaption></figure>")
    page = f"""<!doctype html>
<html lang='es'><head><meta charset='utf-8'><meta name='viewport' content='width=device-width,initial-scale=1'>
<title>VINOVA PRO · Deployment Smoke</title>
<style>
body{{font-family:Arial,sans-serif;margin:0;background:#f4f7fb;color:#16243a}}main{{max-width:1180px;margin:auto;padding:32px}}header{{background:#123b63;color:white;padding:30px;border-radius:18px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(180px,1fr));gap:14px;margin:20px 0}}.card{{background:white;padding:18px;border-radius:14px;box-shadow:0 8px 24px #17324d14}}table{{width:100%;border-collapse:collapse;background:white;border-radius:14px;overflow:hidden}}th,td{{padding:12px;border-bottom:1px solid #dce5ee;text-align:left;vertical-align:top}}.status{{font-weight:bold}}.passed{{color:#08783e}}.warning{{color:#8a5a00}}.failed{{color:#b42318}}.skipped{{color:#52606d}}.captures{{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}}figure{{margin:0;background:white;padding:12px;border-radius:12px}}img{{max-width:100%;height:auto;border-radius:8px}}code{{font-size:.86em}}</style></head>
<body><main><header><h1>VINOVA PRO</h1><h2>Validación automatizada post-despliegue</h2><p>Modo {html.escape(report['mode'])} · versión {html.escape(report['source_version'])} · objetivo {html.escape(report['target_url'])}</p></header>
<section class='grid'><article class='card'><strong>Estado</strong><p>{html.escape(report['status'].upper())}</p></article><article class='card'><strong>Deployment ready</strong><p>{str(report['deployment_ready']).lower()}</p></article><article class='card'><strong>Duración</strong><p>{report['duration_seconds']} s</p></article><article class='card'><strong>Controles</strong><p>{len(state.checks)}</p></article></section>
<h2>Resultados</h2><table><thead><tr><th>Escenario</th><th>Control</th><th>Estado</th><th>Detalle</th><th>Evidencia</th></tr></thead><tbody>{''.join(rows)}</tbody></table>
{_role_matrix_html(state)}
<h2>Capturas</h2><section class='captures'>{''.join(captures) or '<p>Sin capturas.</p>'}</section>
<h2>Conclusión</h2><p>{'La instalación cumple los controles obligatorios ejecutados.' if report['deployment_ready'] else 'La instalación no cumple uno o más controles obligatorios o quedaron controles requeridos sin ejecutar.'}</p>
</main></body></html>"""
    path = state.output_dir / "report.html"
    path.write_text(page, encoding="utf-8")
    return path


def write_evidence_zip(state: RunState) -> Path:
    path = state.output_dir / "evidence.zip"
    with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for item in sorted(state.output_dir.rglob("*")):
            if item.is_file() and item != path:
                archive.write(item, item.relative_to(state.output_dir).as_posix())
    return path


def finalize_reports(state: RunState) -> dict[str, str]:
    state.output_dir.mkdir(parents=True, exist_ok=True)
    summary = state.write_summary()
    junit = write_junit(state)
    html_path = write_html(state)
    evidence = write_evidence_zip(state)
    return {
        "summary": str(summary),
        "junit": str(junit),
        "html": str(html_path),
        "evidence": str(evidence),
    }
