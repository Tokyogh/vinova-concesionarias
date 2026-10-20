"""ES: Este módulo especifica regresiones ejecutables para el dominio de infraestructura compartida.

EN: This module specifies executable regressions for the common domain.

Contexto existente / Existing context:
Regression coverage for search helpers in the common domain.
"""

from apps.common.search import (
    clean_identification_query,
    clean_name_query,
    clean_phone_query,
    clean_search_query,
    normalize_plate,
    normalize_vin,
    plate_startswith_q,
)


def test_clean_search_query_trims_and_collapses():
    assert clean_search_query("  Hola   mundo  ") == "Hola mundo"


def test_clean_search_query_rejects_short_and_oversized():
    assert clean_search_query("") == ""
    assert clean_search_query("a") == ""
    assert clean_search_query("x" * 200) == "x" * 80


def test_clean_name_query_uses_own_minimum():
    assert clean_name_query("a") == ""
    assert clean_name_query("ab") == "ab"


def test_clean_identification_query_keeps_digits_only():
    assert clean_identification_query("0911-4532-15") == "0911453215"
    assert clean_identification_query("12345") == ""


def test_clean_phone_query_keeps_digits_only():
    assert clean_phone_query("+593 99 123 4567") == "593991234567"
    assert clean_phone_query("12345") == ""


def test_normalize_plate_and_vin():
    assert normalize_plate(" abc-1234 ") == "ABC1234"
    assert normalize_plate("ab") == ""
    assert normalize_vin("vin-search-0001") == "VINSEARCH0001"
    assert normalize_vin("short") == ""


def test_plate_startswith_q_is_separator_tolerant():
    q = plate_startswith_q("abc-1234")
    assert str(q) == "(AND: ('plate__iregex', '^A[^A-Z0-9]*B[^A-Z0-9]*C[^A-Z0-9]*1[^A-Z0-9]*2[^A-Z0-9]*3[^A-Z0-9]*4'))"


def test_plate_startswith_q_empty_for_short_input():
    assert not plate_startswith_q("ab")
    assert not plate_startswith_q("")
