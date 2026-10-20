# -*- coding: utf-8 -*-
"""ES: Este módulo implementa el componente portal parity para el dominio de operación y QA.

EN: This module implements the portal parity component for the operations and QA domain.

Contexto existente / Existing context:
Capture comparable LITE/PRO portal states without persisting credentials.

Credentials are accepted only through environment variables. Generated evidence
is written below ``run/portal-parity`` (ignored by git).
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from PIL import Image, ImageChops, ImageEnhance, ImageStat
from playwright.sync_api import Page, sync_playwright


VIEWPORTS = {
    "1440x900": (1440, 900),
    "768x1024": (768, 1024),
    "390x844": (390, 844),
}

LITE_SECTIONS = (
    "inicio",
    "mis-vehiculos",
    "agregar-vehiculo",
    "historial",
    "proximos-servicios",
    "manuales",
    "facturas",
    "perfil",
    "notificaciones",
    "configuracion",
)

PRO_PATHS = {
    "inicio": "/mi-cuenta/",
    "vehiculos": "/mi-cuenta/vehiculos/",
    "agregar": "/mi-cuenta/vehiculos/agregar/",
    "historial": "/mi-cuenta/servicios/?view=history",
    "servicios": "/mi-cuenta/servicios/?view=upcoming",
    "manuales": "/mi-cuenta/documentos/",
    "facturas": "/mi-cuenta/facturas/",
    "perfil": "/mi-cuenta/perfil/",
    "notificaciones": "/mi-cuenta/notificaciones/",
    "configuracion": "/mi-cuenta/configuracion/",
}

LITE_TO_REPORT = {
    "inicio": "inicio",
    "mis-vehiculos": "vehiculos",
    "agregar-vehiculo": "agregar",
    "historial": "historial",
    "proximos-servicios": "servicios",
    "manuales": "manuales",
    "facturas": "facturas",
    "perfil": "perfil",
    "notificaciones": "notificaciones",
    "configuracion": "configuracion",
}

MEASURE_JS = """
() => {
  const first = (...selectors) => selectors.map((s) => document.querySelector(s)).find(Boolean);
  const box = (element) => {
    if (!element) return null;
    const rect = element.getBoundingClientRect();
    const style = getComputedStyle(element);
    return {
      x: Math.round(rect.x), y: Math.round(rect.y),
      width: Math.round(rect.width), height: Math.round(rect.height),
      display: style.display, position: style.position,
      padding: style.padding, gap: style.gap,
      fontSize: style.fontSize, borderRadius: style.borderRadius,
      background: style.backgroundColor, color: style.color,
    };
  };
  const root = document.documentElement;
  return {
    url: location.pathname + location.hash,
    title: document.title,
    viewport: {width: innerWidth, height: innerHeight},
    document: {
      width: root.scrollWidth, height: root.scrollHeight,
      horizontalOverflow: root.scrollWidth > root.clientWidth + 1,
    },
    sidebar: box(first('.sidebar', '.portal-sidebar', '.portal-nav')),
    header: box(first('.main-header', '.portal-topbar', '.portal-heading')),
    content: box(first('.main-content', '.portal-main', '.portal-content')),
    firstCard: box(first('.stat-card', '.summary-card', '.portal-metric-card', '.panel-card')),
    modal: box(first('.vehicle-modal.show', '.modal.show', '[role=dialog]:not([hidden])')),
    navigation: [...document.querySelectorAll('.sidebar a, .portal-sidebar a, .portal-nav a')]
      .map((element) => element.textContent.trim()).filter(Boolean).slice(0, 16),
    headings: [...document.querySelectorAll('h1,h2')]
      .map((element) => element.textContent.trim()).filter(Boolean).slice(0, 20),
    visibleSections: [...document.querySelectorAll('section')]
      .filter((element) => {
        const style = getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        return style.display !== 'none' && !element.hidden && rect.width > 0 && rect.height > 0;
      }).map((element) => element.id || element.className).slice(0, 20),
  };
}
"""


def args_parser() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--label", default="baseline")
    parser.add_argument("--out", default="run/portal-parity")
    return parser.parse_args()


def login_lite(page: Page, base: str) -> None:
    page.goto(f"{base}/login", wait_until="domcontentloaded", timeout=60_000)
    page.fill("#email", os.environ["VINOVA_LITE_QA_USER"])
    page.fill("#password", os.environ["VINOVA_LITE_QA_PASS"])
    page.locator("form[action='/login'] button[type='submit']").click()
    page.wait_for_url("**/perfil**", timeout=60_000)


def login_pro(page: Page, base: str) -> None:
    page.goto(f"{base}/accounts/login/", wait_until="domcontentloaded", timeout=60_000)
    page.fill("#id_username", os.environ["VINOVA_PRO_QA_USER"])
    page.fill("#id_password", os.environ["VINOVA_PRO_QA_PASS"])
    page.locator("form button.btn-primary").click()
    page.wait_for_load_state("networkidle")
    if "/accounts/login/" in page.url:
        raise RuntimeError("PRO QA authentication did not leave the login screen")


def capture(page: Page, destination: Path, key: str) -> dict:
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(450)
    measurement = page.evaluate(MEASURE_JS)
    page.screenshot(path=str(destination / f"{key}.png"), full_page=True)
    return measurement


def create_visual_comparisons(root: Path) -> dict[str, dict]:
    """Create review-only overlays/diffs; palette differences are intentional."""
    comparison_root = root / "comparisons"
    comparison_root.mkdir(exist_ok=True)
    report: dict[str, dict] = {}
    for viewport_name in VIEWPORTS:
        for section in PRO_PATHS:
            lite_path = root / f"lite-{viewport_name}-{section}.png"
            pro_path = root / f"pro-{viewport_name}-{section}.png"
            if not lite_path.exists() or not pro_path.exists():
                continue
            with Image.open(lite_path).convert("RGB") as lite_source, Image.open(pro_path).convert("RGB") as pro_source:
                width = min(lite_source.width, pro_source.width)
                height = min(lite_source.height, pro_source.height)
                lite = lite_source.crop((0, 0, width, height))
                pro = pro_source.crop((0, 0, width, height))
                key = f"{viewport_name}-{section}"
                Image.blend(lite, pro, 0.5).save(comparison_root / f"overlay-{key}.png")
                raw_diff = ImageChops.difference(lite, pro)
                ImageEnhance.Contrast(raw_diff).enhance(2.5).save(comparison_root / f"diff-{key}.png")
                mean = ImageStat.Stat(raw_diff).mean
                report[key] = {
                    "compared_width": width,
                    "compared_height": height,
                    "mean_absolute_rgb_percent": round(sum(mean) / (3 * 255) * 100, 2),
                    "lite_full_height": lite_source.height,
                    "pro_full_height": pro_source.height,
                }
    return report


def main() -> int:
    """ES: Orquesta «portal parity» con fallos controlados para operación y QA.

    EN: Orchestrates «portal parity» with controlled failures for operations and QA.
    """

    args = args_parser()
    root = Path(args.out) / args.label
    root.mkdir(parents=True, exist_ok=True)
    lite_base = os.getenv("VINOVA_LITE_BASE", "http://127.0.0.1:5001").rstrip("/")
    pro_base = os.getenv("VINOVA_PRO_BASE", "http://127.0.0.1:8000").rstrip("/")
    report: dict[str, dict] = {}

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(args=["--no-sandbox"])
        for viewport_name, (width, height) in VIEWPORTS.items():
            for product in ("lite", "pro"):
                context = browser.new_context(viewport={"width": width, "height": height}, locale="es-EC")
                page = context.new_page()
                try:
                    if product == "lite":
                        login_lite(page, lite_base)
                        for section in LITE_SECTIONS:
                            trigger = page.locator(f"[data-section='{section}'], [href='#{section}']").first
                            if trigger.count():
                                trigger.click()
                                page.wait_for_timeout(150)
                            key = f"{product}-{viewport_name}-{LITE_TO_REPORT[section]}"
                            report[key] = capture(page, root, key)
                    else:
                        login_pro(page, pro_base)
                        for section, path in PRO_PATHS.items():
                            page.goto(f"{pro_base}{path}", wait_until="domcontentloaded", timeout=60_000)
                            key = f"{product}-{viewport_name}-{section}"
                            report[key] = capture(page, root, key)
                except Exception as exc:  # noqa: BLE001
                    report[f"{product}-{viewport_name}-error"] = {"error": str(exc)[:500]}
                finally:
                    context.close()
        browser.close()

    report["_comparisons"] = create_visual_comparisons(root)
    (root / "measurements.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    failures = [key for key, value in report.items() if "error" in value]
    print(f"captured={len(report) - len(failures)} failures={len(failures)} out={root}")
    for failure in failures:
        print(f"ERROR {failure}: {report[failure]['error']}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
