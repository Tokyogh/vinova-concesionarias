#!/usr/bin/env python3
"""ES: Este módulo implementa el componente optimize vinova assets para el dominio de operación y QA.

EN: This module implements the optimize vinova assets component for the operations and QA domain.

Contexto existente / Existing context:
Build the final VINOVA WebP set from the user-supplied source photographs.

The source files in ``tilin`` remain untouched. Output metadata is stripped and
two smaller responsive variants are generated alongside each canonical asset.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from PIL import Image, ImageOps


ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / "tilin"
OUTPUT_DIR = ROOT / "static" / "img" / "vinova"
QUALITY = 84
VARIANT_WIDTHS = (640, 960)

ASSETS = {
    "Imagen de ChatGPT 7 oct 2026, 20_47_11.png": "01_dashboard-welcome.webp",
    "Imagen de ChatGPT 7 oct 2026, 20_27_04.png": "02_hero-home.webp",
    "Imagen de ChatGPT 7 oct 2026, 20_27_40.png": "03_vehicle-catalog-blue.webp",
    "Imagen de ChatGPT 7 oct 2026, 20_29_06.png": "04_vehicle-catalog-silver.webp",
    "Imagen de ChatGPT 7 oct 2026, 20_33_03.png": "05_vehicle-catalog-dark.webp",
    "Imagen de ChatGPT 7 oct 2026, 20_38_47.png": "06_workshop-services.webp",
    "Imagen de ChatGPT 7 oct 2026, 20_40_26.png": "07_showroom-about.webp",
    "Imagen de ChatGPT 7 oct 2026, 20_48_07.png": "08_contact-location.webp",
    "Imagen de ChatGPT 7 oct 2026, 20_49_00.png": "09_auth-cover.webp",
}


def save_webp(image: Image.Image, destination: Path) -> None:
    image.save(destination, "WEBP", quality=QUALITY, method=6, optimize=True)


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    missing = [name for name in ASSETS if not (SOURCE_DIR / name).is_file()]
    if missing:
        raise SystemExit(f"Missing VINOVA source assets: {', '.join(missing)}")

    for source_name, output_name in ASSETS.items():
        source = SOURCE_DIR / source_name
        destination = OUTPUT_DIR / output_name
        with Image.open(source) as opened:
            image = ImageOps.exif_transpose(opened).convert("RGB")
            save_webp(image, destination)
            for width in VARIANT_WIDTHS:
                height = round(image.height * width / image.width)
                variant = image.resize((width, height), Image.Resampling.LANCZOS)
                save_webp(variant, destination.with_name(f"{destination.stem}-{width}.webp"))

        digest = hashlib.sha256(destination.read_bytes()).hexdigest()[:12]
        print(
            f"{source_name} -> {destination.relative_to(ROOT)} "
            f"({image.width}x{image.height}, {destination.stat().st_size} bytes, sha256:{digest})"
        )


if __name__ == "__main__":
    main()
