"""ES: Este módulo implementa el componente compare para el dominio de operación y QA.

EN: This module implements the compare component for the operations and QA domain.

Contexto existente / Existing context:
Compare a rebuilt screenshot against its reference panel, numerically.

Both images are normalised to the same CSS width (1440). Metrics reported:

  * header band height (first full-width light band at the top)
  * section band boundaries (row luminance/colour steps)
  * primary-blue rects (buttons, accents)
  * navy surface rects (staff sidebar, dark media)
  * palette distance (mean abs RGB diff over a 24-colour histogram)

Usage:
  python scripts/ui/compare.py --shot run/ui/f16-final-public/home-1440x900-light.png       --ref docs/ui/panels/panel_01.png --name home
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
SCALE = 600.0 / 1440.0
PANELS = {
    "home": 1, "catalog": 2, "detail": 3, "services": 4,
    "about": 5, "contact": 6, "login": 7, "dashboard": 8,
}


def to_width(img: Image.Image, width: int = 1440) -> Image.Image:
    if img.width == width:
        return img
    ratio = width / img.width
    return img.resize((width, max(1, round(img.height * ratio))), Image.LANCZOS)


def header_height(a: np.ndarray) -> int | None:
    """First full-width near-uniform light band, measured from the top."""
    h = a.shape[0]
    for y in range(4, min(h, 200)):
        row = a[y]
        if row.std(axis=0).mean() < 6 and row.mean() > 200:
            y2 = y
            while y2 < h and a[y2].std(axis=0).mean() < 8 and a[y2].mean() > 200:
                y2 += 1
            if y2 - y >= 36:
                return y - 0
    return None


def band_edges(a: np.ndarray, min_len: int = 12) -> list[int]:
    """Rows where the row signature changes materially (section boundaries)."""
    h = a.shape[0]
    row = a.reshape(h, -1, 3).astype(np.float32)
    sig = np.stack([row[:, :, 0].mean(1), row[:, :, 1].mean(1), row[:, :, 2].mean(1),
                    row.std(axis=1).mean(axis=1)], axis=1)
    out = []
    last = sig[0]
    for y in range(1, h):
        d = np.abs(sig[y] - last).max()
        if d > 6 and y - (out[-1] if out else 0) >= min_len:
            out.append(int(y))
        last = last * 0.75 + sig[y] * 0.25
    return out


def color_rects(a: np.ndarray, kind: str) -> list[tuple[int, int, int, int]]:
    """ES: Ejecuta la operación «color rects» dentro del dominio de operación y QA.

    EN: Executes the «color rects» operation within the operations and QA domain.
    """

    r = a[:, :, 0].astype(np.int16)
    g = a[:, :, 1].astype(np.int16)
    b = a[:, :, 2].astype(np.int16)
    if kind == "blue":
        m = (b > 120) & (b < 250) & (r < 100) & (g > 55) & (g < 175) & (b - r > 60)
    elif kind == "navy":
        m = (r < 60) & (g < 85) & (b > 35) & (b < 135) & (g <= b + 10)
    else:
        m = (r > 246) & (g > 246) & (b > 246)
    h, w = m.shape
    seen = np.zeros_like(m, dtype=bool)
    out = []
    for y in range(h):
        for x in np.flatnonzero(m[y]):
            if seen[y, x]:
                continue
            y1 = y
            while y1 + 1 < h and m[y1 + 1, x] and not seen[y1 + 1, x]:
                y1 += 1
            x1 = x
            while x1 + 1 < w and m[y1, x1 + 1] and not seen[y1, x1 + 1]:
                x1 += 1
            bw, bh = x1 - x + 1, y1 - y + 1
            if bw >= 24 and bh >= 10:
                seen[y : y1 + 1, x : x1 + 1] = True
                out.append((int(x), int(y), int(bw), int(bh)))
    return out


def hist(a: np.ndarray, bins: int = 8) -> np.ndarray:
    q = (a.reshape(-1, 3)[::4] // 16).astype(np.int32)
    key = q[:, 0] * (bins ** 2) + q[:, 1] * bins + q[:, 2]
    h = np.bincount(key, minlength=bins ** 3).astype(np.float64)
    return h / max(1.0, h.sum())


def palette_distance(x: np.ndarray, y: np.ndarray) -> float:
    return float(np.abs(hist(x) - hist(y)).sum() * 100)


def metrics(a: np.ndarray) -> dict:
    out = {"h": int(a.shape[0]), "header": header_height(a), "bands": band_edges(a)[:26]}
    out["blue"] = sorted(color_rects(a, "blue"), key=lambda r: -(r[2] * r[3]))[:10]
    out["navy"] = sorted(color_rects(a, "navy"), key=lambda r: -(r[2] * r[3]))[:8]
    out["white"] = sorted(color_rects(a, "white"), key=lambda r: -(r[2] * r[3]))[:8]
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--shot", required=True)
    ap.add_argument("--ref", default=None)
    ap.add_argument("--name", required=True)
    ap.add_argument("--crop-height", type=int, default=0)
    args = ap.parse_args()

    shot = np.asarray(to_width(Image.open(args.shot).convert("RGB")))
    if args.crop_height:
        shot = shot[: args.crop_height]
    m = metrics(shot)
    print(f"== {args.name} shot {shot.shape[1]}x{shot.shape[0]} ==")
    print(json.dumps(m, indent=1))

    if args.ref or (ROOT / "docs" / "ui" / "panels").exists():
        ref_path = Path(args.ref) if args.ref else (
            ROOT / "docs" / "ui" / "panels" / f"panel_{PANELS[args.name]:02d}.png"
        )
        if ref_path.exists():
            ref = np.asarray(to_width(Image.open(ref_path).convert("RGB")))
            if shot.shape[0] > ref.shape[0]:
                shot = shot[: ref.shape[0]]
            else:
                ref = ref[: shot.shape[0]]
            r = metrics(ref)
            print(f"== {args.name} reference {ref.shape[1]}x{ref.shape[0]} ==")
            print(json.dumps(r, indent=1))
            print(f"palette distance: {palette_distance(shot, ref):.1f}%")
            print(f"header: shot={m['header']} ref={r['header']}")
            print(f"bands shot={m['bands']}")
            print(f"bands ref ={r['bands']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
