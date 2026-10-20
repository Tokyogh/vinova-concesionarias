"""ES: Este módulo centraliza validaciones contextuales para el dominio de infraestructura compartida.

EN: This module centralizes contextual validation for the common domain.

Contexto existente / Existing context:
Validadores contextuales compartidos por los dominios de VINOVA PRO.

Context-specific validators shared across VINOVA PRO domains.
"""

import re
import unicodedata
import zipfile
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path, PurePosixPath

from cryptography.hazmat.primitives.serialization import pkcs12
from django.conf import settings
from django.core.exceptions import ValidationError

IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
AVATAR_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.webp'}
AVATAR_FORMATS = {'JPEG', 'PNG', 'WEBP'}
DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.csv', '.p12', '.pfx'}
MODEL_3D_EXTENSIONS = {'.glb', '.gltf', '.usdz'}
VIDEO_EXTENSIONS = {'.mp4', '.webm', '.mov'}

_OLE2_HEADER = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
_ZIP_REQUIRED_NAMES = {
    '.docx': ('[Content_Types].xml', 'word/document.xml'),
    '.xlsx': ('[Content_Types].xml', 'xl/workbook.xml'),
}

_PKCS7_DATA_OID = b"\x2a\x86\x48\x86\xf7\x0d\x01\x07\x01"
_PKCS7_ENCRYPTED_DATA_OID = b"\x2a\x86\x48\x86\xf7\x0d\x01\x07\x06"
_PKCS12_BAG_OID_PREFIX = b"\x2a\x86\x48\x86\xf7\x0d\x01\x0c\x0a\x01"
_MP4_BRANDS = {
    b"avc1",
    b"dash",
    b"iso2",
    b"iso3",
    b"iso4",
    b"iso5",
    b"iso6",
    b"isom",
    b"M4V ",
    b"mp41",
    b"mp42",
}


def _read_prefix(value, size=4096):
    try:
        value.seek(0)
        data = value.read(size)
        value.seek(0)
    except Exception:
        return b""
    return data or b""


def _check_pdf(value):
    return _read_prefix(value, 5).startswith(b"%PDF-")


def _check_ole2(value):
    return _read_prefix(value, 8) == _OLE2_HEADER


def _der_tlv(data, offset):
    if offset + 2 > len(data):
        raise ValueError
    tag = data[offset]
    first_length = data[offset + 1]
    cursor = offset + 2
    if first_length & 0x80:
        length_bytes = first_length & 0x7F
        if length_bytes == 0 or length_bytes > 4 or cursor + length_bytes > len(data):
            raise ValueError
        length = int.from_bytes(data[cursor : cursor + length_bytes], "big")
        cursor += length_bytes
    else:
        length = first_length
    end = cursor + length
    if end > len(data):
        raise ValueError
    return tag, cursor, end


def _der_expected(data, offset, expected_tag):
    tag, start, end = _der_tlv(data, offset)
    if tag != expected_tag:
        raise ValueError
    return start, end


def _valid_algorithm_identifier(data, offset, parent_end):
    start, end = _der_expected(data, offset, 0x30)
    oid_start, oid_end = _der_expected(data, start, 0x06)
    if oid_start == oid_end or end > parent_end:
        raise ValueError
    cursor = oid_end
    if cursor < end:
        _, _, cursor = _der_tlv(data, cursor)
    if cursor != end:
        raise ValueError
    return end


def _valid_mac_data(data, offset, pfx_end):
    start, end = _der_expected(data, offset, 0x30)
    if end != pfx_end:
        return False
    digest_start, digest_end = _der_expected(data, start, 0x30)
    cursor = _valid_algorithm_identifier(data, digest_start, digest_end)
    value_start, cursor = _der_expected(data, cursor, 0x04)
    if value_start == cursor or cursor != digest_end:
        return False
    salt_start, cursor = _der_expected(data, digest_end, 0x04)
    if salt_start == cursor:
        return False
    if cursor < end:
        iterations_start, cursor = _der_expected(data, cursor, 0x02)
        if iterations_start == cursor or int.from_bytes(data[iterations_start:cursor], "big") < 1:
            return False
    return cursor == end


def _valid_safe_contents(data):
    start, end = _der_expected(data, 0, 0x30)
    if end != len(data) or start == end:
        return False
    cursor = start
    while cursor < end:
        bag_start, bag_end = _der_expected(data, cursor, 0x30)
        oid_start, oid_end = _der_expected(data, bag_start, 0x06)
        oid = data[oid_start:oid_end]
        if len(oid) != len(_PKCS12_BAG_OID_PREFIX) + 1 or not oid.startswith(_PKCS12_BAG_OID_PREFIX):
            return False
        value_start, value_end = _der_expected(data, oid_end, 0xA0)
        if value_start == value_end:
            return False
        bag_cursor = value_end
        if bag_cursor < bag_end:
            _, _, bag_cursor = _der_tlv(data, bag_cursor)
        if bag_cursor != bag_end:
            return False
        cursor = bag_end
    return cursor == end


def _valid_encrypted_data(data, start, end):
    encrypted_start, encrypted_end = _der_expected(data, start, 0x30)
    if encrypted_end != end:
        return False
    version_start, cursor = _der_expected(data, encrypted_start, 0x02)
    if version_start == cursor:
        return False
    info_start, info_end = _der_expected(data, cursor, 0x30)
    oid_start, cursor = _der_expected(data, info_start, 0x06)
    if data[oid_start:cursor] != _PKCS7_DATA_OID:
        return False
    cursor = _valid_algorithm_identifier(data, cursor, info_end)
    encrypted_content_start, cursor = _der_expected(data, cursor, 0x80)
    if encrypted_content_start == cursor or cursor != info_end:
        return False
    return info_end == encrypted_end


def _valid_password_protected_authenticated_safe(data):
    start, end = _der_expected(data, 0, 0x30)
    if end != len(data) or start == end:
        return False
    cursor = start
    encrypted_content_found = False
    while cursor < end:
        info_start, info_end = _der_expected(data, cursor, 0x30)
        oid_start, info_cursor = _der_expected(data, info_start, 0x06)
        content_oid = data[oid_start:info_cursor]
        explicit_start, explicit_end = _der_expected(data, info_cursor, 0xA0)
        if explicit_end != info_end:
            return False
        if content_oid == _PKCS7_DATA_OID:
            safe_start, safe_end = _der_expected(data, explicit_start, 0x04)
            if safe_end != explicit_end or not _valid_safe_contents(data[safe_start:safe_end]):
                return False
        elif content_oid == _PKCS7_ENCRYPTED_DATA_OID:
            if not _valid_encrypted_data(data, explicit_start, explicit_end):
                return False
            encrypted_content_found = True
        else:
            return False
        cursor = info_end
    return cursor == end and encrypted_content_found


def _check_pkcs12(value):
    try:
        value.seek(0)
        data = value.read()
        value.seek(0)

        pfx_start, pfx_end = _der_expected(data, 0, 0x30)
        if pfx_end != len(data):
            return False
        version_start, cursor = _der_expected(data, pfx_start, 0x02)
        if data[version_start:cursor] != b"\x03":
            return False
        auth_start, auth_end = _der_expected(data, cursor, 0x30)
        oid_start, auth_cursor = _der_expected(data, auth_start, 0x06)
        if data[oid_start:auth_cursor] != _PKCS7_DATA_OID:
            return False
        explicit_start, explicit_end = _der_expected(data, auth_cursor, 0xA0)
        payload_start, payload_end = _der_expected(data, explicit_start, 0x04)
        if payload_start == payload_end or payload_end != explicit_end or explicit_end != auth_end:
            return False

        try:
            key, certificate, additional = pkcs12.load_key_and_certificates(data, None)
        except ValueError:
            key = certificate = additional = None
        if key is not None or certificate is not None or additional:
            return True

        return (
            auth_end < pfx_end
            and _valid_mac_data(data, auth_end, pfx_end)
            and _valid_password_protected_authenticated_safe(data[payload_start:payload_end])
        )
    except (TypeError, ValueError, IndexError):
        return False


def _check_csv(value):
    data = _read_prefix(value)
    if b"\x00" in data:
        return False
    try:
        decoded = data.decode("utf-8-sig")
    except UnicodeDecodeError:
        return False
    return bool(decoded.strip())


def _check_jpeg(value):
    return _read_prefix(value, 3) == b"\xff\xd8\xff"


def _check_png(value):
    return _read_prefix(value, 8) == b"\x89PNG\r\n\x1a\n"


def _check_webp(value):
    data = _read_prefix(value, 12)
    return data[:4] == b"RIFF" and data[8:12] == b"WEBP"


def _zip_member_name_is_safe(name):
    """Rechaza rutas ambiguas o con traversal sin extraer el archivo.

    Rejects ambiguous or traversal-prone paths without extracting the archive.
    """

    if not name or "\\" in name or any(ord(character) < 32 for character in name):
        return False
    path = PurePosixPath(name)
    return not path.is_absolute() and ".." not in path.parts and not path.parts[0].endswith(":")


def _zip_names(value):
    """Inspecciona un ZIP con límites de metadatos y expansión.

    Inspects a ZIP container with bounded metadata and expansion limits.
    """

    try:
        value.seek(0)
        with zipfile.ZipFile(value) as archive:
            members = archive.infolist()
            max_entries = settings.VINOVA_ZIP_MAX_ENTRIES
            max_uncompressed_bytes = settings.VINOVA_ZIP_MAX_UNCOMPRESSED_MB * 1024 * 1024
            max_ratio = settings.VINOVA_ZIP_MAX_COMPRESSION_RATIO
            if len(members) > max_entries:
                return None

            names = set()
            normalized_names = set()
            total_uncompressed = 0
            for member in members:
                if member.flag_bits & 0x1 or not _zip_member_name_is_safe(member.filename):
                    return None
                normalized_name = member.filename.casefold()
                if member.filename in names or normalized_name in normalized_names:
                    return None
                names.add(member.filename)
                normalized_names.add(normalized_name)
                total_uncompressed += member.file_size
                if total_uncompressed > max_uncompressed_bytes:
                    return None
                if member.file_size and member.compress_size == 0:
                    return None
                if member.compress_size and member.file_size / member.compress_size > max_ratio:
                    return None
    except (OSError, ValueError, zipfile.BadZipFile, zipfile.LargeZipFile):
        return None
    finally:
        try:
            value.seek(0)
        except Exception:
            pass
    return names


def _check_zip_container(value, required_names=()):
    names = _zip_names(value)
    if names is None:
        return False
    if required_names:
        return all(name in names for name in required_names)
    return True


def _check_usdz(value):
    names = _zip_names(value)
    if not names:
        return False
    return any(name.endswith((".usd", ".usdc", ".usda")) for name in names)


def _check_glb(value):
    return _read_prefix(value, 4) == b"glTF"


def _check_gltf(value):
    data = _read_prefix(value)
    stripped = data.lstrip(b"\xef\xbb\xbf \t\r\n")
    return stripped.startswith(b"{") and b'"asset"' in data


def _check_iso_bmff(value, allowed_brands):
    data = _read_prefix(value, 512)
    if len(data) < 16 or data[4:8] != b"ftyp":
        return False
    box_size = int.from_bytes(data[:4], "big")
    if box_size < 16 or box_size > len(data):
        return False
    brands = {data[8:12]}
    brands.update(data[offset : offset + 4] for offset in range(16, box_size, 4))
    return bool(brands & allowed_brands)


def _check_webm(value):
    return _read_prefix(value, 4) == b"\x1a\x45\xdf\xa3"


_CONTENT_CHECKERS = {
    '.jpg': _check_jpeg,
    '.jpeg': _check_jpeg,
    '.png': _check_png,
    '.webp': _check_webp,
    '.pdf': _check_pdf,
    '.doc': _check_ole2,
    '.xls': _check_ole2,
    '.docx': lambda value: _check_zip_container(value, required_names=_ZIP_REQUIRED_NAMES['.docx']),
    '.xlsx': lambda value: _check_zip_container(value, required_names=_ZIP_REQUIRED_NAMES['.xlsx']),
    '.usdz': _check_usdz,
    '.csv': _check_csv,
    '.p12': _check_pkcs12,
    '.pfx': _check_pkcs12,
    '.glb': _check_glb,
    '.gltf': _check_gltf,
    '.mp4': lambda value: _check_iso_bmff(value, _MP4_BRANDS),
    '.mov': lambda value: _check_iso_bmff(value, {b"qt  "}),
    '.webm': _check_webm,
}


def validate_upload_extension(value):
    suffix = Path(value.name).suffix.lower()
    if suffix not in (IMAGE_EXTENSIONS | DOCUMENT_EXTENSIONS | MODEL_3D_EXTENSIONS | VIDEO_EXTENSIONS):
        raise ValidationError(f'Extensión no permitida: {suffix}')
    max_bytes = settings.VINOVA_MAX_UPLOAD_MB * 1024 * 1024
    if value.size is not None and value.size > max_bytes:
        return
    checker = _CONTENT_CHECKERS.get(suffix)
    if checker is not None and not checker(value):
        raise ValidationError(f'El archivo no corresponde al tipo real esperado para la extensión {suffix}')


def validate_upload_size(value):
    max_bytes = settings.VINOVA_MAX_UPLOAD_MB * 1024 * 1024
    if value.size > max_bytes:
        raise ValidationError(f'El archivo supera {settings.VINOVA_MAX_UPLOAD_MB} MB')


def validate_avatar_image(value):
    """Valida una imagen de avatar real (formato, decodificación y dimensiones).

    Usa Pillow para comprobar que el contenido es una imagen decodificable del
    tipo esperado; un archivo con extensión válida pero contenido distinto se
    rechaza. También bloquea bombas de descompresión (Pillow) y aplica límites
    de tamaño y dimensiones configurables por entorno.
    """

    from PIL import Image, UnidentifiedImageError

    max_bytes = settings.VINOVA_AVATAR_MAX_MB * 1024 * 1024
    if getattr(value, 'size', None) is not None and value.size > max_bytes:
        raise ValidationError(f'La imagen supera {settings.VINOVA_AVATAR_MAX_MB} MB.')

    suffix = Path(value.name).suffix.lower()
    if suffix not in AVATAR_EXTENSIONS:
        raise ValidationError('Formato no permitido. Usa una imagen JPG, PNG o WEBP.')

    try:
        value.seek(0)
        with Image.open(value) as image:
            image.verify()
        value.seek(0)
        with Image.open(value) as image:
            image_format = image.format
            width, height = image.size
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise ValidationError('El archivo no es una imagen válida.') from exc
    finally:
        try:
            value.seek(0)
        except (AttributeError, ValueError):
            pass

    if image_format not in AVATAR_FORMATS:
        raise ValidationError('Formato de imagen no permitido. Usa JPG, PNG o WEBP.')

    min_dimension = settings.VINOVA_AVATAR_MIN_DIMENSION
    max_dimension = settings.VINOVA_AVATAR_MAX_DIMENSION
    if width < min_dimension or height < min_dimension:
        raise ValidationError(f'La imagen debe medir al menos {min_dimension}×{min_dimension} píxeles.')
    if width > max_dimension or height > max_dimension:
        raise ValidationError(f'La imagen no debe superar {max_dimension}×{max_dimension} píxeles.')


_EC_CEDULA_COEFFICIENTS = (2, 1, 2, 1, 2, 1, 2, 1, 2)
_EC_RUC_PUBLIC_COEFFICIENTS = (3, 2, 7, 6, 5, 4, 3, 2)
_EC_RUC_PRIVATE_COEFFICIENTS = (4, 3, 2, 7, 6, 5, 4, 3, 2)


def _ec_digits(value) -> str:
    from apps.common.normalization import identification_digits

    return identification_digits(value)


def is_valid_ec_cedula(value) -> bool:
    cedula = _ec_digits(value)
    if len(cedula) != 10 or not cedula.isdigit():
        return False
    if cedula == cedula[0] * 10:
        return False
    province = int(cedula[:2])
    if province < 1 or province > 24:
        return False
    if int(cedula[2]) >= 6:
        return False
    total = 0
    for index in range(9):
        product = int(cedula[index]) * _EC_CEDULA_COEFFICIENTS[index]
        if product >= 10:
            product -= 9
        total += product
    verifier = (10 - (total % 10)) % 10
    return verifier == int(cedula[9])


def _ec_modulo_11(digits: str, coefficients) -> int | None:
    total = sum(int(digit) * coefficient for digit, coefficient in zip(digits, coefficients))
    result = 11 - (total % 11)
    if result == 11:
        return 0
    if result == 10:
        return None
    return result


def is_valid_ec_ruc(value) -> bool:
    """ES: Ejecuta la operación «is valid ec ruc» dentro del dominio de infraestructura compartida. Además, rechaza estados o entradas inválidas.

    EN: Executes the «is valid ec ruc» operation within the common domain. It also rejects invalid input or state.
    """

    ruc = _ec_digits(value)
    if len(ruc) != 13 or not ruc.isdigit():
        return False
    if ruc == ruc[0] * 13:
        return False
    province = int(ruc[:2])
    if province < 1 or province > 24:
        return False
    if ruc[-3:] == "000":
        return False
    third_digit = int(ruc[2])
    if third_digit < 6:
        return is_valid_ec_cedula(ruc[:10])
    if third_digit == 6:
        verifier = _ec_modulo_11(ruc[:8], _EC_RUC_PUBLIC_COEFFICIENTS)
        return verifier is not None and verifier == int(ruc[8])
    if third_digit == 9:
        verifier = _ec_modulo_11(ruc[:9], _EC_RUC_PRIVATE_COEFFICIENTS)
        return verifier is not None and verifier == int(ruc[9])
    return False


def validate_ec_cedula(value):
    if not is_valid_ec_cedula(value):
        raise ValidationError("Ingresa una cédula ecuatoriana válida de 10 dígitos.")


def validate_ec_ruc(value):
    if not is_valid_ec_ruc(value):
        raise ValidationError("Ingresa un RUC ecuatoriano válido de 13 dígitos.")


def validate_no_unsafe_control_characters(value):
    """ES: Rechaza controles invisibles sin alterar puntuación legítima.

    EN: Rejects invisible control characters without changing legitimate
    punctuation. Newlines and tabs remain valid for multi-line text fields.
    """

    for character in str(value or ""):
        if character in "\n\r\t":
            continue
        if unicodedata.category(character) in {"Cc", "Cf", "Cs"}:
            raise ValidationError("El texto contiene caracteres de control no permitidos.")


def validate_human_name(value):
    """ES: Acepta nombres Unicode reales. EN: Accepts legitimate Unicode names."""

    text = str(value or "").strip()
    if not text:
        return
    validate_no_unsafe_control_characters(text)
    allowed_punctuation = {" ", "-", "'", "’", "."}
    if not any(unicodedata.category(character).startswith("L") for character in text):
        raise ValidationError("Ingresa un nombre que contenga letras.")
    for character in text:
        category = unicodedata.category(character)
        if category.startswith("L") or category.startswith("M") or character in allowed_punctuation:
            continue
        raise ValidationError("El nombre contiene caracteres no permitidos.")


def validate_phone_number(value):
    """ES: Valida teléfonos locales/internacionales sin destruir su formato.

    EN: Validates local/international phone numbers without destructively
    rewriting their presentation.
    """

    text = str(value or "").strip()
    if not text:
        return
    validate_no_unsafe_control_characters(text)
    if not re.fullmatch(r"\+?[0-9() .-]+", text):
        raise ValidationError("Usa únicamente dígitos y los signos + ( ) espacio punto o guion.")
    digits = re.sub(r"\D", "", text)
    if not 7 <= len(digits) <= 15:
        raise ValidationError("El teléfono debe contener entre 7 y 15 dígitos.")


def validate_vehicle_plate(value):
    """ES: Aplica el patrón de placa configurado. EN: Applies the configured plate pattern."""

    text = str(value or "").strip().upper()
    if not text:
        return
    validate_no_unsafe_control_characters(text)
    pattern = getattr(settings, "VINOVA_VEHICLE_PLATE_PATTERN", r"^[A-Z]{2,3}[- ]?\d{3,4}$")
    try:
        matched = re.fullmatch(pattern, text)
    except re.error as exc:
        raise ValidationError("La configuración del formato de placa no es válida.") from exc
    if not matched:
        raise ValidationError("Ingresa una placa válida para la jurisdicción configurada.")


def validate_vehicle_identifier(value):
    """ES: Valida VIN/chasis flexible. EN: Validates a flexible VIN/chassis identifier."""

    text = str(value or "").strip().upper()
    if not text:
        return
    validate_no_unsafe_control_characters(text)
    if not re.fullmatch(r"[A-Z0-9-]{6,40}", text):
        raise ValidationError("El VIN/chasis debe contener entre 6 y 40 letras, números o guiones.")


def validate_vehicle_year(value):
    """ES: Acota años físicamente posibles. EN: Bounds physically plausible vehicle years."""

    if value in (None, ""):
        return
    maximum = date.today().year + 2
    try:
        numeric_year = int(value)
    except (TypeError, ValueError) as exc:
        raise ValidationError("Ingresa un año válido.") from exc
    if not 1886 <= numeric_year <= maximum:
        raise ValidationError(f"El año debe estar entre 1886 y {maximum}.")


def validate_nonnegative_decimal(value):
    """ES: Rechaza importes negativos. EN: Rejects negative monetary values."""

    if value in (None, ""):
        return
    try:
        numeric = Decimal(value)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValidationError("Ingresa un valor decimal válido.") from exc
    if not numeric.is_finite() or numeric < 0:
        raise ValidationError("El valor no puede ser negativo.")


def validate_hex_color(value):
    """ES: Limita colores de marca a RGB hexadecimal. EN: Allows only hexadecimal RGB brand colors."""

    if not re.fullmatch(r"#[0-9A-Fa-f]{6}", str(value or "")):
        raise ValidationError("Usa un color hexadecimal con formato #RRGGBB.")


def safe_hex_color(value, default):
    """ES: Protege estilos ante datos heredados. EN: Safely falls back for legacy style data."""

    try:
        validate_hex_color(value)
    except ValidationError:
        return default
    return str(value)
