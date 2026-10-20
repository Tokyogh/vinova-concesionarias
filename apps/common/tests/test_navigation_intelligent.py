"""ES: Este módulo especifica regresiones ejecutables para el dominio de infraestructura compartida.

EN: This module specifies executable regressions for the common domain.

Contexto existente / Existing context:
Regression coverage for navigation intelligent in the common domain.
"""

from types import SimpleNamespace

import pytest
from django.test import RequestFactory

from apps.common.navigation import ALL_DESTINATIONS, authorized_destinations, current_destination, navigation_context


def _user(**permissions):
    values = {
        "pk": 42,
        "is_authenticated": True,
        "has_perm_code": lambda code: False,
    }
    values.update(permissions)
    return SimpleNamespace(**values)


def test_authorized_destinations_exclude_unavailable_permissions_and_modules():
    user = _user(can_view_customers=True, can_view_inventory=False)
    keys = [item.key for item in authorized_destinations(user, {"post_sales": False})]

    assert keys == ["dashboard", "customers"]
    assert "inventory" not in keys
    assert "post_sales" not in keys


def test_current_destination_uses_specific_exclusion_for_security_alerts():
    destinations = [ALL_DESTINATIONS["audit"], ALL_DESTINATIONS["audit_alerts"]]
    assert current_destination("/dashboard/audit/alerts/", destinations).key == "audit_alerts"


@pytest.mark.django_db
def test_navigation_context_is_permission_filtered_without_sql(django_assert_num_queries):
    request = RequestFactory().get("/dashboard/customers/")
    request.user = _user(can_view_customers=True)

    with django_assert_num_queries(0):
        context = navigation_context(request)

    assert [item["key"] for item in context["staff_nav_json"]["destinations"]] == ["dashboard", "customers"]
    assert context["staff_nav_current_key"] == "customers"
