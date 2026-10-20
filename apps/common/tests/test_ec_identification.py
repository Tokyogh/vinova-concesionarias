"""ES: Este módulo especifica regresiones ejecutables para el dominio de infraestructura compartida.

EN: This module specifies executable regressions for the common domain.

Contexto existente / Existing context:
Regression coverage for ec identification in the common domain.
"""

import pytest
from django.core.exceptions import ValidationError

from apps.common.normalization import identification_digits, normalize_identification
from apps.common.validators import is_valid_ec_cedula, is_valid_ec_ruc, validate_ec_cedula, validate_ec_ruc

VALID_CEDULA = "2458963176"
VALID_RUC_NATURAL = "2458963176001"
VALID_RUC_PUBLIC = "1760012320001"
VALID_RUC_PRIVATE = "1790012344001"


@pytest.mark.parametrize("value", [
    VALID_CEDULA,
    "24 5896 3176",
    "24-5896-3176",
    f" {VALID_CEDULA} ",
])
def test_valid_cedula_accepted(value):
    assert is_valid_ec_cedula(value) is True
    validate_ec_cedula(value)


@pytest.mark.parametrize("value", [
    "2458963177",
    "0911111111",
    "245896317",
    "24589631760",
    "2558963176",
    "1799999999",
    "1111111111",
    "abcdefghij",
    "",
    None,
])
def test_invalid_cedula_rejected(value):
    assert is_valid_ec_cedula(value) is False
    with pytest.raises(ValidationError):
        validate_ec_cedula(value)


@pytest.mark.parametrize("value", [
    VALID_RUC_NATURAL,
    VALID_RUC_PUBLIC,
    VALID_RUC_PRIVATE,
])
def test_valid_ruc_accepted(value):
    assert is_valid_ec_ruc(value) is True
    validate_ec_ruc(value)


@pytest.mark.parametrize("value", [
    "2458963176000",
    "245896317600",
    "24589631760012",
    "1770000000001",
    "1790000000000",
    "2500000000001",
    "1111111111111",
    "abcdefghijklm",
])
def test_invalid_ruc_rejected(value):
    assert is_valid_ec_ruc(value) is False
    with pytest.raises(ValidationError):
        validate_ec_ruc(value)


def test_normalize_identification_strips_separators():
    assert normalize_identification(" 17.110-16091 ") == "1711016091"
    assert normalize_identification(None) == ""
    assert identification_digits("P E 123456") == "123456"
