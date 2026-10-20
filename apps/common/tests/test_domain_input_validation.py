"""Regression coverage for contextual domain input validation.

ES: Comprueba que formularios y API aplican las mismas reglas sin modificar
contraseñas ni destruir texto Unicode legítimo.
EN: Ensures forms and APIs share validation without rewriting passwords or
legitimate Unicode text.
"""

from datetime import date
from decimal import Decimal

import pytest
from django.core.exceptions import ValidationError
from django.test import override_settings

from apps.accounts.forms import ClientRegistrationForm
from apps.api.serializers import ExternalLeadSerializer
from apps.branches.api.serializers import BranchSerializer
from apps.common.validators import (
    validate_human_name,
    validate_hex_color,
    validate_no_unsafe_control_characters,
    validate_nonnegative_decimal,
    validate_phone_number,
    validate_vehicle_identifier,
    validate_vehicle_plate,
    validate_vehicle_year,
    safe_hex_color,
)
from apps.inventory.api.serializers import InventoryItemSerializer
from apps.leads.forms import PublicLeadForm
from apps.vehicles.api.serializers import VehicleSerializer
from apps.vehicles.forms import VehicleForm, VehicleSearchForm


@pytest.mark.parametrize(
    "value",
    ["María-José O’Connor", "Ñusta de la Cruz", "Jose\u0301 Pérez"],
)
def test_human_name_accepts_legitimate_unicode(value):
    validate_human_name(value)


@pytest.mark.parametrize("value", ["Persona 123", "Nombre\u200bOculto", "---"])
def test_human_name_rejects_non_name_or_invisible_content(value):
    with pytest.raises(ValidationError):
        validate_human_name(value)


@pytest.mark.parametrize(
    "value",
    ["0991234567", "+593 (4) 234-5678", "+1 202.555.0199"],
)
def test_phone_accepts_local_and_international_presentation(value):
    validate_phone_number(value)


@pytest.mark.parametrize("value", ["12345", "+593-ABC-123", "1" * 16])
def test_phone_rejects_invalid_content_or_digit_length(value):
    with pytest.raises(ValidationError):
        validate_phone_number(value)


def test_control_character_validator_preserves_normal_multiline_text():
    validate_no_unsafe_control_characters("Av. 6 de Diciembre\nEdificio A\tLocal 2")
    with pytest.raises(ValidationError):
        validate_no_unsafe_control_characters("texto\x00oculto")


@pytest.mark.parametrize("value", ["#006BC7", "#abcdef", "#ABCDEF"])
def test_brand_color_accepts_only_complete_hex_rgb(value):
    validate_hex_color(value)


@pytest.mark.parametrize("value", ["red", "#123", "#123456;body{}", "#GGGGGG"])
def test_brand_color_rejects_css_injection_and_malformed_values(value):
    with pytest.raises(ValidationError):
        validate_hex_color(value)


def test_legacy_invalid_brand_color_falls_back_before_template_rendering():
    assert safe_hex_color("#123456;body{display:none}", "#006BC7") == "#006BC7"


def test_vehicle_validators_cover_plate_identifier_year_and_money():
    validate_vehicle_plate("PBC-1234")
    validate_vehicle_identifier("1HGCM82633A004352")
    validate_vehicle_year(date.today().year + 2)
    validate_nonnegative_decimal(Decimal("0"))

    invalid_values = (
        (validate_vehicle_plate, "123-ABC"),
        (validate_vehicle_identifier, "VIN?"),
        (validate_vehicle_year, 1885),
        (validate_vehicle_year, "no-es-año"),
        (validate_nonnegative_decimal, Decimal("-0.01")),
        (validate_nonnegative_decimal, Decimal("NaN")),
        (validate_nonnegative_decimal, Decimal("Infinity")),
    )
    for validator, value in invalid_values:
        with pytest.raises(ValidationError):
            validator(value)


@override_settings(VINOVA_VEHICLE_PLATE_PATTERN=r"^[A-Z]{1,2}\d{2}$")
def test_vehicle_plate_pattern_is_configurable_by_jurisdiction():
    validate_vehicle_plate("AB12")
    with pytest.raises(ValidationError):
        validate_vehicle_plate("PBC-1234")


def test_forms_attach_validators_to_the_intended_fields_only():
    search_form = VehicleSearchForm()
    vehicle_form = VehicleForm()
    lead_form = PublicLeadForm()

    assert validate_vehicle_year in vehicle_form.fields["year"].validators
    assert validate_vehicle_identifier in vehicle_form.fields["vin"].validators
    assert validate_vehicle_plate in vehicle_form.fields["plate"].validators
    assert validate_nonnegative_decimal in vehicle_form.fields["price"].validators
    assert "year" not in search_form.fields
    assert "price" not in search_form.fields
    assert lead_form.fields["full_name"].clean("María-José O’Connor") == "María-José O’Connor"


def test_password_field_is_not_sanitized_or_rewritten():
    password = "  Clave-Árbol-7! con espacios  "
    assert ClientRegistrationForm.base_fields["password1"].clean(password) == password


@pytest.mark.parametrize(
    ("serializer_class", "data", "field"),
    [
        (BranchSerializer, {"phone": "teléfono-inválido"}, "phone"),
        (VehicleSerializer, {"plate": "123-ABC"}, "plate"),
        (InventoryItemSerializer, {"price": "-1.00"}, "price"),
        (ExternalLeadSerializer, {"phone": "ABC", "full_name": "Cliente Válido"}, "phone"),
    ],
)
def test_api_serializers_enforce_contextual_validation(serializer_class, data, field):
    serializer = serializer_class(data=data, partial=True)
    assert serializer.is_valid() is False
    assert field in serializer.errors
