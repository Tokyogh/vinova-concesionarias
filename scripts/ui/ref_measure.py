"""ES: Este módulo implementa el componente ref measure para el dominio de operación y QA.

EN: This module implements the ref measure component for the operations and QA domain.

Contexto existente / Existing context:
Geometry + palette measurement for the cropped reference panels.

Produces a text report (docs/ui/reference-geometry.md) with per-panel:
  * horizontal section bands and their background colors
  * vertical structure of the header area
  * detected cards, buttons, media blocks, sidebars (rect + size in CSS px)
  * palette histogram

Panel crops are ~0.416x of the 1440px design viewport, so measured pixels are
scaled back with PANEL_SCALE to obtain CSS pixel values.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "ui" / "panels"
DESIGN_W = 1440.0
PANEL_SCALE = 600.0 / DESIGN_W


def q(rgb: np.ndarray, step: int = 4) -> tuple[int, int, int]:
    return tuple(int(v) // step * step for v in rgb)  # type: ignore[return-value]


def row_profile(p: np.ndarray, step: int = 4) -> list[tuple[int, int, tuple[int, int, int], float]]:
    """Runs of rows sharing the same quantized median color."""
    h = p.shape[0]
    med = np.median(p.reshape(h, -1, 3), axis=1)
    keys = np.stack([med[:, 0], med[:, 1], med[:, 2]], axis=1) // step * step
    out = []
    start = 0
    for y in range(1, h + 1):
        cur = tuple(keys[y]) if y < h else None
        if cur != tuple(keys[start]):
            if y - start >= 3:
                seg = p[start:y].reshape(-1, 3)
                out.append((start, y, q(np.median(seg, axis=0)), float(seg.mean())))
            start = y
    return out


def col_profile(p: np.ndarray, step: int = 4) -> list[tuple[int, int, tuple[int, int, int]]]:
    w = p.shape[1]
    med = np.median(p.reshape(-1, w, 3), axis=0)
    keys = np.stack([med[:, 0], med[:, 1], med[:, 2]], axis=1) // step * step
    out = []
    start = 0
    for x in range(1, w + 1):
        if x == w or tuple(keys[x]) != tuple(keys[start]):
            if x - start >= 3:
                seg = p[:, start:x].reshape(-1, 3)
                out.append((start, x, q(np.median(seg, axis=0))))
            start = x
    return out


def is_dark(rgb: tuple[int, int, int]) -> bool:
    return (rgb[0] + rgb[1] + rgb[2]) / 3 < 110


def blocks(p: np.ndarray, target: tuple[int, int, int], tol: int = 14) -> list[tuple[int, int, int, int]]:
    """Axis-aligned rects of a target color (rectangles of >=40x24 css px)."""
    m = (np.abs(p.astype(np.int16) - np.array(target, dtype=np.int16)).max(axis=2) <= tol)
    h, w = m.shape
    seen = np.zeros_like(m, dtype=bool)
    out = []
    for y in range(h):
        row = m[y]
        for x in np.flatnonzero(row):
            if seen[y, x]:
                continue
            y1 = y
            while y1 + 1 < h and m[y1 + 1, x]:
                y1 += 1
            x1 = x
            while x1 + 1 < w and m[y1, x1 + 1]:
                x1 += 1
            if (x1 - x) >= 20 and (y1 - y) >= 8 and (x1 - x) < w * 0.98:
                seen[y : y1 + 1, x : x1 + 1] = True
                out.append((x, y, x1 + 1, y1 + 1))
    return out


def palette(p: np.ndarray, top: int = 14) -> list[tuple[tuple[int, int, int], float]]:
    flat = p.reshape(-1, 3)[::3]
    keys = (flat[:, 0] // 8 * 8, flat[:, 1] // 8 * 8, flat[:, 2] // 8 * 8)
    uniq, counts = np.unique(np.stack(keys, axis=1), axis=0, return_counts=True)
    order = np.argsort(-counts)[:top]
    total = counts.sum()
    return [(tuple(int(v) for v in uniq[j]), counts[j] / total) for j in order]  # type: ignore[misc]


def css(px: float) -> float:
    return round(px / PANEL_SCALE, 1)


def main() -> int:
    meta = json.loads((ROOT / "docs" / "ui" / "reference-panels.json").read_text(encoding="utf-8"))
    lines: list[str] = []
    lines.append("# Reference geometry report\n")
    lines.append(f"panel scale: {PANEL_SCALE:.4f} (crop px / css px, design width {DESIGN_W:.0f})\n")
    for entry in meta:
        path = OUT / entry["file"]
        p = np.asarray(Image.open(path).convert("RGB"))
        h, w, _ = p.shape
        lines.append(f"\n## panel {entry['index']:02d} — {entry['file']} ({w}x{h} crop px, ar {w / h:.2f})\n")
        lines.append("palette:\n")
        for c, pct in palette(p):
            lines.append(f"  #{c[0]:02X}{c[1]:02X}{c[2]:02X} {pct * 100:5.1f}%\n")
        lines.append("\nhorizontal bands (y0,y1,median color,mean lum):\n")
        for (y0, y1, c, lum) in row_profile(p):
            lines.append(f"  {y0:4d}-{y1:4d} (h={css(y1-y0):5.1f}css) #{c[0]:02X}{c[1]:02X}{c[2]:02X} lum={lum:5.1f}\n")
        lines.append("\nvertical bands (x0,x1,median color):\n")
        for (x0, x1, c) in col_profile(p):
            lines.append(f"  {x0:4d}-{x1:4d} (w={css(x1-x0):5.1f}css) #{c[0]:02X}{c[1]:02X}{c[2]:02X}\n")
        for name, target, tol in (
            ("navy blocks", (11, 31, 58), 16),
            ("primary blue blocks", (0, 107, 199), 26),
            ("white cards", (255, 255, 255), 6),
            ("ice surfaces", (247, 249, 252), 5),
            ("blue tint surfaces", (238, 246, 253), 5),
        ):
            bs = blocks(p, target, tol)
            bs = [b for b in bs if (b[2] - b[0]) * (b[3] - b[1]) > 1200]
            if not bs:
                continue
            lines.append(f"\n{name} (#{target[0]:02X}{target[1]:02X}{target[2]:02X}):\n")
            for (x0, y0, x1, y1) in bs[:40]:
                lines.append(
                    f"  x{x0:4d} y{y0:4d} w{css(x1-x0):6.1f} h{css(y1-y0):6.1f} css  @({css(x0)},{css(y0)})\n"
                )
        _ = is_dark
    (ROOT / "docs" / "ui" / "reference-geometry.md").write_text("".join(lines), encoding="utf-8")
    print("wrote docs/ui/reference-geometry.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())