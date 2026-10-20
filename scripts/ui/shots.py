# -*- coding: utf-8 -*-
"""ES: Este módulo implementa el componente shots para el dominio de operación y QA.

EN: This module implements the shots component for the operations and QA domain.

Contexto existente / Existing context:
Visual rebuild harness: screenshots + measured geometry for the 8 screens.

Runs inside the app container (Playwright + chromium already installed):

    docker compose exec -T web python scripts/ui/shots.py --label baseline

Captures light/dark at the given viewports, stores PNGs under run/ui/<label>/
and a geometry JSON with measured boxes and a11y-ish metrics used to compare
against docs/ui/reference-spec.md.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

BASE = os.getenv("VINOVA_UI_BASE", "http://127.0.0.1:8000")
OUT_ROOT = Path(os.getenv("VINOVA_UI_OUT", "run/ui"))
QA_USER = os.getenv("VINOVA_QA_USER", "visualqa")
QA_PASS = os.getenv("VINOVA_QA_PASS", "VisualQA-Local-2026!")

VIEWPORTS = {
    "1440x900": (1440, 900),
    "1366x768": (1366, 768),
    "1280x800": (1280, 800),
    "1024x768": (1024, 768),
    "768x1024": (768, 1024),
    "430x932": (430, 932),
    "390x844": (390, 844),
}

SCREENS = [
    ("home", "/", False),
    ("catalog", "/vehicles/", False),
    ("detail", "/vehicles/{detail_slug}/", False),
    ("services", "/#servicios", False),
    ("about", "/#nosotros", False),
    ("contact", "/leads/request/", False),
    ("login", "/accounts/login/", False),
    ("dashboard", "/dashboard/", True),
]

PROBES = {
    "header": "header",
    "brand": ".public-brand, .brand",
    "nav": ".public-nav",
    "navLink": ".public-nav a",
    "container": ".public-container, .container, main > .wrap",
    "hero": ".public-hero, .hero",
    "h1": "h1",
    "sidebar": "#staff-sidebar, .app-sidebar, .sidebar",
    "mainContent": ".main-content",
    "topbar": ".topbar",
    "kpi": ".kpi-card, .kpi, .metric-card",
    "card": ".card, .public-card, .vehicle-card, .service-card",
    "btnPrimary": ".btn-primary",
    "btn": ".btn",
    "input": "input[type=text], input[type=email], input:not([type])",
    "footer": ".public-footer, footer",
}

GEOMETRY_JS = """
(sel) => {
  const out = {};
  for (const [k, s] of Object.entries(sel)) {
    const el = document.querySelector(s);
    if (!el) { out[k] = null; continue; }
    const r = el.getBoundingClientRect();
    const cs = getComputedStyle(el);
    out[k] = {
      x: Math.round(r.x), y: Math.round(r.y),
      w: Math.round(r.width), h: Math.round(r.height),
      fs: cs.fontSize, fw: cs.fontWeight, lh: cs.lineHeight,
      color: cs.color, bg: cs.backgroundColor, br: cs.borderRadius,
      f: cs.fontFamily.split(',')[0].replace(/"/g, ''),
    };
  }
  const d = document.documentElement, b = document.body;
  out._doc = {
    scrollW: d.scrollWidth, clientW: d.clientWidth,
    scrollH: d.scrollHeight,
    overflowX: d.scrollWidth > d.clientWidth + 1,
    bodyOverflowX: b ? b.scrollWidth > b.clientWidth + 1 : false,
  };
  out._headings = [...document.querySelectorAll('h1,h2')].slice(0, 12).map(e => {
    const r = e.getBoundingClientRect();
    return { tag: e.tagName, text: e.textContent.trim().slice(0, 70),
             fs: getComputedStyle(e).fontSize, w: Math.round(r.width), x: Math.round(r.x) };
  });
  out._navlinks = [...document.querySelectorAll('header nav a, .public-nav a')]
      .slice(0, 10).map(e => e.textContent.trim());
  return out;
}
"""


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--label", default="baseline")
    p.add_argument("--viewports", default="1440x900,390x844")
    p.add_argument("--themes", default="light")
    p.add_argument("--screens", default=",".join(s[0] for s in SCREENS))
    p.add_argument("--full-page", action="store_true", default=True)
    return p.parse_args()


def qa_login(browser, width: int, height: int) -> dict | None:
    """Autentica la cuenta QA y devuelve el storage_state reutilizable."""
    ctx = browser.new_context(viewport={"width": width, "height": height}, locale="es-EC")
    page = ctx.new_page()
    try:
        for attempt in range(3):
            try:
                page.goto(f"{BASE}/accounts/login/", wait_until="load", timeout=60000)
                page.fill("#id_username", QA_USER, timeout=60000)
                page.fill("#id_password", QA_PASS, timeout=60000)
                page.click("form button.btn-primary")
                page.wait_for_load_state("networkidle")
                if not page.url.startswith(f"{BASE}/dashboard"):
                    raise RuntimeError(f"login redirected to {page.url}")
                return ctx.storage_state()
            except Exception as exc:  # noqa: BLE001
                if attempt == 2:
                    print(f"[shots] login failed: {exc}"[:300])
                    return None
                page.wait_for_timeout(2000)
    finally:
        page.close()
        ctx.close()


def resolve_detail_slug(page) -> str:
    """Resuelve el slug publico del primer vehiculo disponible en el catalogo."""

    page.goto(f"{BASE}/vehicles/", wait_until="load", timeout=60000)
    href = page.evaluate(
        """() => {
            const link = document.querySelector('.vehicle-details-link')
                || [...document.querySelectorAll('.vehicle-card a')].find((a) => a.getAttribute('href').includes('/vehicles/'));
            return link ? link.getAttribute('href') : '';
        }"""
    )
    if not href:
        raise RuntimeError("no hay vehiculo publico para capturar la ficha")
    return href.rstrip("/").split("/")[-1]


def main() -> int:
    """ES: Orquesta «shots» con fallos controlados para operación y QA.

    EN: Orchestrates «shots» with controlled failures for operations and QA.
    """

    args = parse_args()
    out = OUT_ROOT / args.label
    out.mkdir(parents=True, exist_ok=True)
    want = {s.strip() for s in args.screens.split(",") if s.strip()}
    screens = [s for s in SCREENS if s[0] in want]
    vps = [v.strip() for v in args.viewports.split(",") if v.strip()]
    themes = [t.strip() for t in args.themes.split(",") if t.strip()]

    report: dict[str, dict] = {}
    with sync_playwright() as pw:
        browser = pw.chromium.launch(args=["--no-sandbox"])
        for vp in vps:
            w, h = VIEWPORTS.get(vp, (1440, 900))
            # Sesion independiente del tema: se autentica una vez por viewport
            # y se reutiliza el storage_state en un contexto por tema.
            state = None
            if any(needs_auth for _, _, needs_auth in screens):
                state = qa_login(browser, w, h)
            for theme in themes:
                ctx = browser.new_context(
                    viewport={"width": w, "height": h},
                    locale="es-EC",
                    storage_state=state,
                )
                ctx.add_init_script(
                    script="try{localStorage.setItem('vinova-theme', '%s')}catch(e){}" % theme
                )
                for name, path, needs_auth in screens:
                    page = ctx.new_page()
                    try:
                        target = path
                        if "{detail_slug}" in path:
                            target = path.replace("{detail_slug}", resolve_detail_slug(page))
                        page.goto(f"{BASE}{target}", wait_until="load", timeout=60000)
                        page.wait_for_timeout(700)
                        if theme != "light":
                            page.wait_for_timeout(200)
                        geom = page.evaluate(GEOMETRY_JS, PROBES)
                        key = f"{vp}/{theme}/{name}"
                        report[key] = geom
                        page.screenshot(
                            path=str(out / f"{name}-{vp}-{theme}.png"),
                            full_page=bool(args.full_page),
                        )
                        flag = "OVERFLOW" if geom["_doc"]["overflowX"] else "ok"
                        print(f"[shots] {key}: {flag} h={geom['_doc']['scrollH']}")
                    except Exception as exc:  # noqa: BLE001
                        report[f"{vp}/{theme}/{name}"] = {"error": str(exc)[:300]}
                        print(f"[shots] {vp}/{theme}/{name}: ERROR {exc}"[:200])
                    finally:
                        page.close()
            ctx.close()
        browser.close()
    (out / "geometry.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"[shots] wrote {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())