"""ES: Este módulo especifica regresiones ejecutables para el dominio de infraestructura compartida.

EN: This module specifies executable regressions for the common domain.

Contexto existente / Existing context:
Regression coverage for lifecycle in the common domain.
"""

import json
from io import StringIO

import pytest
from django.conf import settings
from django.core.management import call_command

from apps.common.lifecycle import (
    ProductVersion,
    assess_product_upgrade,
    database_migration_state,
    installation_lifecycle_state,
)


def test_lifecycle_versions_are_explicit_and_independent():
    assert str(ProductVersion.parse(settings.VINOVA_PRODUCT_VERSION)) == settings.VINOVA_PRODUCT_VERSION
    assert isinstance(settings.VINOVA_BACKUP_FORMAT_VERSION, int)
    assert isinstance(settings.VINOVA_TRANSFER_FORMAT_VERSION, int)
    assert settings.VINOVA_BACKUP_FORMAT_VERSION != settings.VINOVA_TRANSFER_FORMAT_VERSION


@pytest.mark.parametrize("invalid", ["2", "2.0", "v2.0.0", "2.0.0-beta", ""])
def test_product_version_rejects_ambiguous_values(invalid):
    with pytest.raises(ValueError):
        ProductVersion.parse(invalid)


def test_upgrade_requires_release_compatibility_and_verified_migration_path():
    blocked_path = assess_product_upgrade(
        "2.0.0", "3.0.0", migration_path_available=False, release_compatible=True
    )
    blocked_release = assess_product_upgrade(
        "2.0.0", "2.1.0", migration_path_available=True, release_compatible=False
    )
    allowed = assess_product_upgrade(
        "2.0.0", "2.1.0", migration_path_available=True, release_compatible=True
    )

    assert not blocked_path["allowed"]
    assert not blocked_release["allowed"]
    assert allowed == {
        "allowed": True,
        "direction": "upgrade",
        "requires_backup": True,
        "downgrade_supported": False,
        "reason": "Upgrade forward permitido; requiere preflight y backup verificado.",
    }


def test_downgrade_is_never_presented_as_safe():
    assessment = assess_product_upgrade(
        "3.0.0", "2.0.0", migration_path_available=True, release_compatible=True
    )

    assert not assessment["allowed"]
    assert assessment["direction"] == "downgrade"
    assert not assessment["downgrade_supported"]
    assert "restore verificado" in assessment["reason"]


@pytest.mark.django_db
def test_database_migration_state_is_separate_and_current():
    state = database_migration_state()

    assert state["kind"] == "django-migration-ledger"
    assert state["is_current"]
    assert state["pending"] == []
    assert state["applied_count"] > 0
    assert len(state["fingerprint_sha256"]) == 64


@pytest.mark.django_db
def test_lifecycle_command_emits_machine_readable_contract():
    output = StringIO()
    call_command("show_vinova_lifecycle", "--json", stdout=output)
    payload = json.loads(output.getvalue())

    assert payload == installation_lifecycle_state()
    assert payload["product_version"] == settings.VINOVA_PRODUCT_VERSION
    assert payload["downgrade_policy"] == "unsupported-use-verified-restore"
