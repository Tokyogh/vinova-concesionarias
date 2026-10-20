"""ES: Este módulo especifica regresiones ejecutables para el dominio de infraestructura compartida.

EN: This module specifies executable regressions for the common domain.

Contexto existente / Existing context:
Regression coverage for ui assets in the common domain.
"""

from pathlib import Path

from apps.common.templatetags.ui_assets import FINAL_ASSETS, ui_final_asset, ui_final_srcset


EXPECTED_PHOTO_PATHS = {
    "dashboard-welcome": "img/vinova/01_dashboard-welcome.webp",
    "home-hero": "img/vinova/02_hero-home.webp",
    "vehicle-catalog-blue": "img/vinova/03_vehicle-catalog-blue.webp",
    "vehicle-catalog-silver": "img/vinova/04_vehicle-catalog-silver.webp",
    "vehicle-catalog-dark": "img/vinova/05_vehicle-catalog-dark.webp",
    "workshop-services": "img/vinova/06_workshop-services.webp",
    "showroom-about": "img/vinova/07_showroom-about.webp",
    "contact-branch": "img/vinova/08_contact-location.webp",
    "auth-cover": "img/vinova/09_auth-cover.webp",
}

SUSPICIOUS_ENCODING_MARKERS = ("\u00c3", "\u00c2", "\ufffd", "\u01ed", "\u01e7")


def test_final_asset_registry_uses_canonical_vinova_manifest():
    assert {slot: FINAL_ASSETS[slot] for slot in EXPECTED_PHOTO_PATHS} == EXPECTED_PHOTO_PATHS
    assert all(Path(path).suffix == ".webp" for path in EXPECTED_PHOTO_PATHS.values())


def test_missing_final_asset_keeps_fallback_without_broken_url(settings, tmp_path):
    settings.STATICFILES_DIRS = [tmp_path]

    assert ui_final_asset("home-hero") == ""
    assert ui_final_srcset("home-hero") == ""
    assert ui_final_asset("unknown-slot") == ""
    assert ui_final_srcset("unknown-slot") == ""


def test_final_assets_decode_as_real_webp_with_responsive_variants():
    from PIL import Image

    static_root = Path(__file__).resolve().parents[3] / "static"
    for relative_path in EXPECTED_PHOTO_PATHS.values():
        canonical = static_root / relative_path
        assert canonical.is_file()
        with Image.open(canonical) as image:
            assert image.format == "WEBP"
            assert image.width >= 1600
            assert image.height >= 900
        for width in (640, 960):
            variant = canonical.with_name(f"{canonical.stem}-{width}.webp")
            assert variant.is_file()
            with Image.open(variant) as image:
                assert image.format == "WEBP"
                assert image.width == width

    srcset = ui_final_srcset("home-hero")
    assert "02_hero-home-640.webp 640w" in srcset
    assert "02_hero-home-960.webp 960w" in srcset
    assert "02_hero-home.webp 1672w" in srcset


def test_active_ui_sources_are_free_from_mojibake_and_demo_branding():
    root = Path(__file__).resolve().parents[3]
    paths = list((root / "templates").rglob("*.html"))
    paths.extend(
        path
        for path in (root / "apps").rglob("*.py")
        if "migrations" not in path.parts and "tests" not in path.parts
    )
    violations = []
    for path in paths:
        content = path.read_text(encoding="utf-8")
        if any(marker in content for marker in SUSPICIOUS_ENCODING_MARKERS):
            violations.append(f"encoding:{path.relative_to(root)}")
        if path.suffix == ".html" and any(label in content.casefold() for label in ("vinova demo", "demo motors", "lorem ipsum")):
            violations.append(f"demo:{path.relative_to(root)}")

    assert violations == []
