"""ES: Este módulo implementa el componente ref panels para el dominio de operación y QA.

EN: This module implements the ref panels component for the operations and QA domain.

Contexto existente / Existing context:
Extract the eight reference panels from the collage.

Background is a light-blue gradient; panels are opaque screenshots. Panels are
found with union-find over per-row non-background intervals, then cropped and
profiled (dominant colors) into docs/ui/panels/.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[2]
REF = ROOT / "docs" / "ui" / "reference-v2.png"
OUT = ROOT / "docs" / "ui" / "panels"


def background_mask(arr: np.ndarray) -> np.ndarray:
    r = arr[:, :, 0].astype(np.int16)
    g = arr[:, :, 1].astype(np.int16)
    b = arr[:, :, 2].astype(np.int16)
    lum = (r + g + b) / 3.0
    return (lum > 205) & (b - r > 8) & (b > 225) & (g > 215)


def row_intervals(mask_row: np.ndarray, min_len: int = 6) -> list[tuple[int, int]]:
    out: list[tuple[int, int]] = []
    start = None
    for i, v in enumerate(mask_row):
        if v and start is None:
            start = i
        elif not v and start is not None:
            if i - start >= min_len:
                out.append((start, i))
            start = None
    if start is not None and len(mask_row) - start >= min_len:
        out.append((start, len(mask_row)))
    return out


def main() -> int:
    """ES: Orquesta «ref panels» con fallos controlados para operación y QA.

    EN: Orchestrates «ref panels» with controlled failures for operations and QA.
    """

    arr = np.asarray(Image.open(REF).convert("RGB"))
    h, w, _ = arr.shape
    fg = ~background_mask(arr)

    parent: dict[tuple[int, int, int], int] = {}
    box: dict[tuple[int, int, int], tuple[int, int, int, int]] = {}
    prev: list[tuple[int, int, tuple[int, int, int]]] = []

    def find(a: int) -> int:
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a: int, b: int) -> int:
        ra, rb = find(a), find(b)
        if ra == rb:
            return ra
        parent[rb] = ra
        ba, bb = box[ra], box[rb]
        box[ra] = (
            min(ba[0], bb[0]),
            max(ba[1], bb[1]),
            min(ba[2], bb[2]),
            max(ba[3], bb[3]),
        )
        return ra

    for y in range(h):
        cur: list[tuple[int, int, tuple[int, int, int]]] = []
        for (x0, x1) in row_intervals(fg[y]):
            key = (y, x0, x1)
            parent[key] = key
            box[key] = (y, y + 1, x0, x1)
            for (px0, px1, pkey) in prev:
                if px1 > x0 and px0 < x1:
                    union(key, pkey)
            cur.append((x0, x1, key))
        prev = cur

    merged = {}
    for key in parent:
        r = find(key)
        b = box[r]
        if b not in merged:
            merged[b] = 0
        merged[b] += 1

    cands = [(b, n) for b, n in merged.items() if (b[1] - b[0]) * (b[3] - b[2]) > 60000]
    cands.sort(key=lambda t: (t[0][0] // 60, t[0][2]))
    print(f"detected {len(cands)} panels")

    img = Image.open(REF).convert("RGB")
    OUT.mkdir(parents=True, exist_ok=True)
    report = []
    for i, (b, area) in enumerate(cands, start=1):
        y0, y1, x0, x1 = b
        crop = img.crop((x0, y0, x1, y1))
        name = f"panel_{i:02d}.png"
        crop.save(OUT / name)
        sub = np.asarray(crop).reshape(-1, 3)[::4]
        keys = (sub[:, 0] // 8 * 8, sub[:, 1] // 8 * 8, sub[:, 2] // 8 * 8)
        uniq, counts = np.unique(np.stack(keys, axis=1), axis=0, return_counts=True)
        order = np.argsort(-counts)[:10]
        dom = [
            f"#{int(uniq[j][0]):02X}{int(uniq[j][1]):02X}{int(uniq[j][2]):02X}"
            f"({counts[j] / len(sub) * 100:.0f}%)"
            for j in order
            if counts[j] / len(sub) > 0.008
        ]
        print(f"  {i:02d} x{x0:4d} y{y0:4d} w{x1-x0:4d} h{y1-y0:4d} ar={(x1-x0)/(y1-y0):.2f} fill={area/((x1-x0)*(y1-y0)):.2f}")
        print(f"      {' '.join(dom)}")
        report.append({"index": i, "file": name, "x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0, "dominant": dom})
    (ROOT / "docs" / "ui" / "reference-panels.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())