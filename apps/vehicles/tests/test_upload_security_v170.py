"""ES: Este módulo especifica regresiones ejecutables para el dominio de vehículos.

EN: This module specifies executable regressions for the vehicles domain.

Contexto existente / Existing context:
Regression coverage for upload security v170 in the vehicles domain.
"""

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings

from apps.vehicles.forms import VehicleMediaUploadForm
from apps.vehicles.models import VehicleMedia

VALID_PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"


def media_form(*, media_type, filename, content=VALID_PDF):
    return VehicleMediaUploadForm(
        data={"media_type": media_type, "order": 0, "is_public": True},
        files={"file": SimpleUploadedFile(filename, content)},
    )


def test_vehicle_media_rejects_extension_that_does_not_match_selected_type():
    form = media_form(media_type=VehicleMedia.MediaType.IMAGE, filename="manual.pdf")

    assert form.is_valid() is False
    assert "no corresponde" in form.errors["file"][0]


@override_settings(VINOVA_MAX_UPLOAD_MB=1)
def test_vehicle_media_rejects_oversized_upload():
    form = media_form(
        media_type=VehicleMedia.MediaType.MANUAL,
        filename="manual.pdf",
        content=b"x" * (1024 * 1024 + 1),
    )

    assert form.is_valid() is False
    assert "supera 1 MB" in form.errors["file"][0]


def test_vehicle_media_accepts_allowed_manual_extension():
    form = media_form(media_type=VehicleMedia.MediaType.MANUAL, filename="manual.pdf")

    assert form.is_valid() is True
