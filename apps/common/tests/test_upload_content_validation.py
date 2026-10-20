"""ES: Este módulo especifica regresiones ejecutables para el dominio de infraestructura compartida.

EN: This module specifies executable regressions for the common domain.

Contexto existente / Existing context:
Regression coverage for upload content validation in the common domain.
"""

import io
import zipfile
from datetime import UTC, datetime, timedelta

import pytest
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.common.validators import validate_upload_extension, validate_upload_size

VALID_PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF\n"
VALID_PNG = b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde"
VALID_JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 32
VALID_WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 "
VALID_CSV = b"ruc,nombre\n1799999999002,Acme\n"
VALID_OLE2 = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 32
VALID_GLB = b"glTF" + b"\x02\x00\x00\x00" + b"\x00" * 32
VALID_GLTF = b'{"asset": {"version": "2.0"}}'
VALID_MP4 = b"\x00\x00\x00\x18ftypisom\x00\x00\x02\x00isomiso2"
VALID_MOV = b"\x00\x00\x00\x14ftypqt  \x00\x00\x00\x00qt  "
VALID_WEBM = b"\x1a\x45\xdf\xa3" + b"\x00" * 32


def _pkcs12_bytes(encryption):
    key = rsa.generate_private_key(public_exponent=65537, key_size=1024)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Vinova upload test")])
    now = datetime.now(UTC)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    return pkcs12.serialize_key_and_certificates(
        b"vinova-test",
        key,
        certificate,
        None,
        encryption,
    )


VALID_PKCS12 = _pkcs12_bytes(serialization.BestAvailableEncryption(b"test-password"))
VALID_PKCS12_WITHOUT_PASSWORD = _pkcs12_bytes(serialization.NoEncryption())
ARTIFICIAL_PKCS12 = bytes.fromhex("3015020103301006092a864886f70d010701a003040100")


def _zip_bytes(*members, compression=zipfile.ZIP_STORED):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=compression) as archive:
        for name, data in members:
            archive.writestr(name, data)
    return buf.getvalue()


VALID_DOCX = _zip_bytes(("[Content_Types].xml", b"<Types/>"), ("word/document.xml", b"<w:document/>"))
VALID_XLSX = _zip_bytes(("[Content_Types].xml", b"<Types/>"), ("xl/workbook.xml", b"<workbook/>"))
ZIP_WITHOUT_DOCX = _zip_bytes(("[Content_Types].xml", b"<Types/>"))
ZIP_WITHOUT_XLSX = _zip_bytes(("[Content_Types].xml", b"<Types/>"), ("xl/sheets/sheet1.xml", b"<sheet/>"))


def _upload(filename, content, content_type="application/octet-stream"):
    return SimpleUploadedFile(filename, content, content_type=content_type)


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("doc.pdf", VALID_PDF),
        ("foto.png", VALID_PNG),
        ("shot.jpg", VALID_JPEG),
        ("portada.webp", VALID_WEBP),
        ("manual.docx", VALID_DOCX),
        ("datos.xlsx", VALID_XLSX),
        ("informe.csv", VALID_CSV),
        ("legacy.doc", VALID_OLE2),
        ("tabla.xls", VALID_OLE2),
        ("certificado.p12", VALID_PKCS12),
        ("llave.pfx", VALID_PKCS12),
        ("certificado-sin-clave.p12", VALID_PKCS12_WITHOUT_PASSWORD),
        ("modelo.glb", VALID_GLB),
        ("escena.gltf", VALID_GLTF),
        ("video.mp4", VALID_MP4),
        ("video.mov", VALID_MOV),
        ("clip.webm", VALID_WEBM),
    ],
)
def test_real_content_accepted_for_allowed_formats(filename, content):
    validate_upload_extension(_upload(filename, content))


def test_allowed_extension_with_fake_content_rejected():
    with pytest.raises(ValidationError):
        validate_upload_extension(_upload("doc.pdf", b"contenido falso"))
    with pytest.raises(ValidationError):
        validate_upload_extension(_upload("foto.png", b"no es una imagen"))


def test_false_client_mime_with_real_content_accepted():
    validate_upload_extension(_upload("doc.pdf", VALID_PDF, content_type="application/x-msdownload"))
    validate_upload_extension(_upload("foto.png", VALID_PNG, content_type="text/plain"))


def test_renamed_file_of_another_type_rejected():
    with pytest.raises(ValidationError):
        validate_upload_extension(_upload("doc.pdf", VALID_PNG))
    with pytest.raises(ValidationError):
        validate_upload_extension(_upload("foto.png", VALID_PDF))
    with pytest.raises(ValidationError):
        validate_upload_extension(_upload("video.mp4", VALID_PDF))
    with pytest.raises(ValidationError):
        validate_upload_extension(_upload("video.mp4", VALID_MOV))
    with pytest.raises(ValidationError):
        validate_upload_extension(_upload("video.mov", VALID_MP4))


def test_pkcs12_requires_a_real_pfx_structure_not_only_a_sequence_byte():
    with pytest.raises(ValidationError):
        validate_upload_extension(_upload("certificado.p12", b"\x30\x82\x01\x00" + b"\x00" * 32))
    with pytest.raises(ValidationError):
        validate_upload_extension(_upload("certificado.p12", ARTIFICIAL_PKCS12))


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("manual.docx", VALID_XLSX),
        ("datos.xlsx", VALID_DOCX),
        ("manual.docx", ZIP_WITHOUT_DOCX),
        ("datos.xlsx", ZIP_WITHOUT_XLSX),
        ("manual.docx", _zip_bytes(("word/document.xml", b"<w:document/>"))),
        ("datos.xlsx", _zip_bytes(("xl/workbook.xml", b"<workbook/>"))),
        ("manual.docx", b"PK\x03\x04 no es un zip real"),
        ("datos.xlsx", b"hola"),
    ],
)
def test_zip_containers_require_matching_internal_structure(filename, content):
    with pytest.raises(ValidationError):
        validate_upload_extension(_upload(filename, content))


def test_zip_container_rejects_too_many_members(settings):
    settings.VINOVA_ZIP_MAX_ENTRIES = 2
    content = _zip_bytes(
        ("[Content_Types].xml", b"<Types/>"),
        ("xl/workbook.xml", b"<workbook/>"),
        ("xl/worksheets/sheet1.xml", b"<sheet/>"),
    )
    with pytest.raises(ValidationError):
        validate_upload_extension(_upload("datos.xlsx", content))


def test_zip_container_rejects_unsafe_or_duplicate_member_names():
    unsafe = _zip_bytes(
        ("[Content_Types].xml", b"<Types/>"),
        ("xl/workbook.xml", b"<workbook/>"),
        ("../payload.xml", b"payload"),
    )
    duplicate = _zip_bytes(
        ("[Content_Types].xml", b"<Types/>"),
        ("xl/workbook.xml", b"<workbook/>"),
        ("XL/WORKBOOK.XML", b"duplicate"),
    )
    for content in (unsafe, duplicate):
        with pytest.raises(ValidationError):
            validate_upload_extension(_upload("datos.xlsx", content))


def test_zip_container_rejects_excessive_expansion(settings):
    settings.VINOVA_ZIP_MAX_COMPRESSION_RATIO = 5
    content = _zip_bytes(
        ("[Content_Types].xml", b"<Types/>"),
        ("xl/workbook.xml", b"0" * 50_000),
        compression=zipfile.ZIP_DEFLATED,
    )
    with pytest.raises(ValidationError):
        validate_upload_extension(_upload("datos.xlsx", content))


def test_zip_container_rejects_excessive_total_uncompressed_size(settings):
    settings.VINOVA_ZIP_MAX_UNCOMPRESSED_MB = 1
    content = _zip_bytes(
        ("[Content_Types].xml", b"<Types/>"),
        ("xl/workbook.xml", b"x" * (1024 * 1024 + 1)),
    )
    with pytest.raises(ValidationError):
        validate_upload_extension(_upload("datos.xlsx", content))


@pytest.mark.parametrize(
    ("filename", "content"),
    [
        ("shell.php", b"<?php ?>"),
        ("malware.exe", b"MZ"),
        ("x.html", b"<script>"),
        ("payload.svg", b"<svg>"),
    ],
)
def test_disallowed_extension_still_blocked(filename, content):
    with pytest.raises(ValidationError):
        validate_upload_extension(_upload(filename, content))


def test_oversized_content_reports_size_error(settings):
    settings.VINOVA_MAX_UPLOAD_MB = 1
    oversized = _upload("grande.pdf", b"x" * (1024 * 1024 + 1))
    with pytest.raises(ValidationError) as excinfo:
        validate_upload_size(oversized)
    assert "supera 1 MB" in str(excinfo.value)


def test_oversized_upload_with_fake_content_passes_through_to_size_validator(settings):
    settings.VINOVA_MAX_UPLOAD_MB = 1
    validate_upload_extension(_upload("grande.pdf", b"x" * (1024 * 1024 + 1)))
    with pytest.raises(ValidationError):
        validate_upload_size(_upload("grande.pdf", b"x" * (1024 * 1024 + 1)))
