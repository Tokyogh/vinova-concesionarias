"""ES: Este módulo implementa el componente ref spec para el dominio de operación y QA.

EN: This module implements the ref spec component for the operations and QA domain.

Contexto existente / Existing context:
Compact, actionable spec extracted from the reference panels.

Emits docs/ui/reference-spec.md: header geometry, content container edges,
primary button rects, navy surface rects, card rects and palette per panel,
all converted to CSS pixels.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs" / "ui" / "panels"
SCALE = 600.0 / 1440.0
NAMES = {
    1: "home",
    2: "catalog",
    3: "vehicle-detail",
    4: "services",
    5: "about",
    6: "contact",
    7: "login",
    8: "dashboard",
}


def css(v: float) -> str:
    return f"{v / SCALE:.0f}"


def rects(mask: np.ndarray, min_w: int = 12, min_h: int = 6, max_frac: float = 0.99) -> list[tuple[int, int, int, int]]:
    h, w = mask.shape
    seen = np.zeros_like(mask, dtype=bool)
    out: list[tuple[int, int, int, int]] = []
    for y in range(h):
        xs = np.flatnonzero(mask[y])
        for x in xs:
            if seen[y, x]:
                continue
            y1 = y
            while y1 + 1 < h and mask[y1 + 1, x] and not seen[y1 + 1, x]:
                y1 += 1
            x1 = x
            while x1 + 1 < w and mask[y1, x1 + 1] and not seen[y1, x1 + 1]:
                x1 += 1
            bw, bh = x1 - x + 1, y1 - y + 1
            if bw >= min_w and bh >= min_h and bw <= w * max_frac:
                seen[y : y1 + 1, x : x1 + 1] = True
                out.append((x, y, x1 + 1, y1 + 1))
    return out


def band_edges(p: np.ndarray, y0: int, y1: int, bg: tuple[int, int, int], tol: int = 10) -> tuple[int, int] | None:
    """Left/right css-x of content that differs from the band background."""
    sub = p[y0:y1].astype(np.int16)
    diff = (np.abs(sub - np.array(bg, dtype=np.int16)).max(axis=2) > tol).any(axis=0)
    xs = np.flatnonzero(diff)
    if len(xs) == 0:
        return None
    return int(xs[0]), int(xs[-1])


def top_color(p: np.ndarray, y0: int, y1: int, x0: int, x1: int) -> tuple[int, int, int]:
    seg = p[y0:y1, x0:x1].reshape(-1, 3)
    med = np.median(seg, axis=0)
    return tuple(int(v // 8 * 8) for v in med)  # type: ignore[return-value]


def main() -> int:
    """Convert measured reference panels into reviewable UI specifications."""

    meta = json.loads((ROOT / "docs" / "ui" / "reference-panels.json").read_text(encoding="utf-8"))
    res: list[str] = ["# Reference spec (CSS px, design width 1440)\n"]
    dump: dict[str, dict] = {}
    for entry in meta:
        i = entry["index"]
        p = np.asarray(Image.open(OUT / entry["file"]).convert("RGB"))
        h, w, _ = p.shape
        key = NAMES.get(i, f"panel{i}")
        lines = [f"\n## {i:02d} {key}  (crop {w}x{h}, css {css(w)}x{css(h)})\n"]

        # ---- full width uniform bands (header / section separators)
        med = np.median(p.reshape(h, -1, 3), axis=1)
        bands: list[tuple[int, int]] = []
        start = 0
        for y in range(1, h + 1):
            if y == h or tuple(med[y]) != tuple(med[start]):
                if y - start >= 4:
                    bands.append((start, y))
                start = y
        lines.append("full-width uniform bands:\n")
        for (y0, y1) in bands:
            c = top_color(p, y0, y1, 0, w)
            lines.append(f"  y {css(y0):>4}-{css(y1):<4} (h={css(y1-y0):>4}) #{c[0]:02X}{c[1]:02X}{c[2]:02X}\n")

        # ---- primary blue rects
        r, g, b = p[:, :, 0].astype(np.int16), p[:, :, 1].astype(np.int16), p[:, :, 2].astype(np.int16)
        blue = (b > 120) & (b < 250) & (r < 90) & (g > 60) & (g < 170) & (b - r > 70)
        br = [x for x in rects(blue, min_w=14, min_h=7)]
        lines.append("primary-blue rects:\n")
        for (x0, y0, x1, y1) in br[:24]:
            lines.append(f"  x {css(x0):>4} y {css(y0):>4}  w={css(x1-x0):>4} h={css(y1-y0):>4}\n")

        # ---- navy rects
        navy = (r < 60) & (g < 80) & (b > 40) & (b < 130) & (r < g + 5) & (g <= b)
        nr = [x for x in rects(navy, min_w=20, min_h=20)]
        lines.append("navy rects:\n")
        for (x0, y0, x1, y1) in nr[:20]:
            lines.append(f"  x {css(x0):>4} y {css(y0):>4}  w={css(x1-x0):>4} h={css(y1-y0):>4}\n")

        # ---- white card rects on non-white bg
        white = (r > 246) & (g > 246) & (b > 246)
        wr = [x for x in rects(white, min_w=40, min_h=24)]
        lines.append("white blocks (cards/panels):\n")
        for (x0, y0, x1, y1) in wr[:30]:
            lines.append(f"  x {css(x0):>4} y {css(y0):>4}  w={css(x1-x0):>4} h={css(y1-y0):>4}\n")

        # ---- content edges in a few key bands
        lines.append("content edges per band:\n")
        for (y0, y1) in bands:
            if y1 - y0 < 6:
                continue
            bg = top_color(p, y0, y1, 0, w)
            e = band_edges(p, y0, y1, bg, tol=12)
            if e:
                lines.append(f"  y {css(y0):>4}: x {css(e[0]):>4} .. {css(e[1]):<5} (bg #{bg[0]:02X}{bg[1]:02X}{bg[2]:02X})\n")

        # ---- text line bands (dark pixels) -> font size hints
        dark = (r < 150) & (g < 150) & (b < 170)
        rowdark = dark.sum(axis=1)
        runs = []
        s = None
        for y in range(h):
            if rowdark[y] >= 1 and s is None:
                s = y
            elif rowdark[y] == 0 and s is not None:
                if y - s >= 3:
                    runs.append((s, y))
                s = None
        if s is not None:
            runs.append((s, h))
        lines.append("dark-row bands (text/graphic rows):\n")
        for (y0, y1) in runs[:40]:
            lines.append(f"  y {css(y0):>4}-{css(y1):<4} h={css(y1-y0):>3}\n")

        res.extend(lines)
        dump[key] = {"crop": [w, h], "bands": [[int(a), int(b)] for a, b in bands]}
    (ROOT / "docs" / "ui" / "reference-spec.md").write_text("".join(res), encoding="utf-8")
    (ROOT / "docs" / "ui" / "reference-spec.json").write_text(json.dumps(dump, indent=2), encoding="utf-8")
    print("wrote docs/ui/reference-spec.md")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
