"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for evidence in the e2e helpers domain.
"""

from __future__ import annotations

import os
from pathlib import Path

from playwright.sync_api import Browser


def create_context(browser: Browser, artifact_root: Path):
    record_video = os.getenv("VINOVA_E2E_RECORD_VIDEO", "False").lower() in {"1", "true", "yes"}
    kwargs = {"viewport": {"width": 1440, "height": 1000}, "locale": "es-EC"}
    if record_video:
        kwargs["record_video_dir"] = str(artifact_root / "videos")
    context = browser.new_context(**kwargs)
    context.tracing.start(screenshots=True, snapshots=True, sources=True)
    return context


def save_context_evidence(context, page, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    persist_trace = os.getenv("VINOVA_E2E_SAVE_TRACE", "True").lower() in {"1", "true", "yes"}
    try:
        page.screenshot(path=str(destination / "final.png"), full_page=True, timeout=120_000)
    finally:
        trace_path = str(destination / "trace.zip") if persist_trace else None
        context.tracing.stop(path=trace_path)
        context.close()
