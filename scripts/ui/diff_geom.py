"""ES: Este módulo implementa el componente diff geom para el dominio de operación y QA.

EN: This module implements the diff geom component for the operations and QA domain.

Contexto existente / Existing context:
Diff two shots.py geometry dumps to verify a phase changed what it should.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ELS = ["header", "brand", "nav", "container", "hero", "h1", "sidebar", "mainContent",
       "topbar", "kpi", "card", "btnPrimary", "btn", "input", "footer"]


def fmt(v: dict | None) -> str:
    if not v:
        return "none"
    return (f"{v['w']}x{v['h']}@{v['x']},{v['y']} {v['fs']}/{v['fw']} "
            f"{v['f']} c={v['color']} bg={v['bg']} r={v['br']}")


def main() -> int:
    """ES: Orquesta «diff geom» con fallos controlados para operación y QA.

    EN: Orchestrates «diff geom» with controlled failures for operations and QA.
    """

    a = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    b = json.loads(Path(sys.argv[2]).read_text(encoding="utf-8"))
    only = sys.argv[3].split(",") if len(sys.argv) > 3 else None
    for key in b:
        if only and key.split("/")[-1] not in only:
            continue
        if key not in a:
            continue
        rows = []
        for el in ELS:
            if a[key].get(el) != b[key].get(el):
                rows.append(f"  {el:11s} {fmt(a[key].get(el))}  ->  {fmt(b[key].get(el))}")
        doc_a, doc_b = a[key]["_doc"], b[key]["_doc"]
        if doc_a != doc_b:
            rows.append(f"  doc        h={doc_a['scrollH']} overflowX={doc_a['overflowX']}"
                        f"  ->  h={doc_b['scrollH']} overflowX={doc_b['overflowX']}")
        ha = [h["text"] for h in a[key]["_headings"]]
        hb = [h["text"] for h in b[key]["_headings"]]
        if ha != hb:
            rows.append(f"  headings   {ha}  ->  {hb}")
        fa = [h["fs"] for h in a[key]["_headings"]]
        fb = [h["fs"] for h in b[key]["_headings"]]
        if fa != fb:
            rows.append(f"  h-sizes    {fa}  ->  {fb}")
        if rows:
            print(key)
            print("\n".join(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())