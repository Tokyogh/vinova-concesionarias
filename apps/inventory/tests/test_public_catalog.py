"""ES: Este módulo especifica regresiones ejecutables para el dominio de inventario.

EN: This module specifies executable regressions for the inventory domain.

Contexto existente / Existing context:
Pruebas del catálogo público y su proyección segura.

Tests for the public catalog and its safe data projection.
"""

from decimal import Decimal

import pytest
from django.test import override_settings
from django.urls import reverse

from apps.branches.models import Branch
from apps.companies.models import Company
from apps.inventory.models import BranchStock, InventoryCategory, InventoryItem


pytestmark = pytest.mark.django_db


@pytest.fixture
def public_catalog_data():
    company = Company.objects.create(
        legal_name="Compañía Sintética S.A.",
        commercial_name="Compañía Sintética",
        ruc="1794444444001",
        is_active=True,
    )
    public_branch = Branch.objects.create(
        company=company,
        name="Sede Pública Norte",
        code="PUBLIC-NORTH",
        branch_type=Branch.BranchType.DEALERSHIP,
        city="Quito",
        is_public=True,
        is_active=True,
    )
    private_branch = Branch.objects.create(
        company=company,
        name="Bodega Privada Secreta",
        code="PRIVATE-STOCK",
        branch_type=Branch.BranchType.WAREHOUSE,
        city="Quito",
        is_public=False,
        is_active=True,
    )
    category = InventoryCategory.objects.create(name="Filtros públicos", slug="filtros-publicos")
    published = InventoryItem.objects.create(
        category=category,
        name="Filtro sintético premium",
        sku="PUB-FILTER-001",
        item_type=InventoryItem.ItemType.FILTER,
        description="Artículo sintético para validar el catálogo.",
        price=Decimal("42.50"),
        cost=Decimal("17.43"),
        is_public=True,
        status=InventoryItem.Status.ACTIVE,
    )
    hidden = InventoryItem.objects.create(
        category=category,
        name="Artículo interno reservado",
        sku="PRIVATE-001",
        item_type=InventoryItem.ItemType.SPARE_PART,
        price=Decimal("99.00"),
        cost=Decimal("61.37"),
        is_public=False,
        status=InventoryItem.Status.ACTIVE,
    )
    service = InventoryItem.objects.create(
        category=category,
        name="Servicio no publicable",
        sku="SERVICE-001",
        item_type=InventoryItem.ItemType.SERVICE,
        price=Decimal("30.00"),
        is_public=True,
        status=InventoryItem.Status.ACTIVE,
        track_stock=False,
    )
    BranchStock.objects.create(
        item=published,
        branch=public_branch,
        quantity=Decimal("91.75"),
        reserved_quantity=Decimal("11.25"),
        minimum_stock=Decimal("7.50"),
        location_code="SECRET-A-99",
    )
    BranchStock.objects.create(
        item=published,
        branch=private_branch,
        quantity=Decimal("8.00"),
        reserved_quantity=Decimal("0.00"),
        location_code="PRIVATE-B-12",
    )
    return {
        "published": published,
        "hidden": hidden,
        "service": service,
        "category": category,
        "public_branch": public_branch,
        "private_branch": private_branch,
    }


@override_settings(VINOVA_PUBLIC_PARTS_CATALOG_ENABLED=True)
def test_public_catalog_exposes_only_explicitly_published_physical_items(client, public_catalog_data):
    response = client.get(reverse("parts:catalog"))
    body = response.content.decode()

    assert response.status_code == 200
    assert list(response.context["items"]) == [public_catalog_data["published"]]
    assert "Filtro sintético premium" in body
    assert "Artículo interno reservado" not in body
    assert "Servicio no publicable" not in body
    assert "17.43" not in body
    assert "61.37" not in body


@override_settings(VINOVA_PUBLIC_PARTS_CATALOG_ENABLED=True)
def test_public_catalog_shows_qualitative_availability_without_internal_stock(client, public_catalog_data):
    response = client.get(reverse("parts:catalog"))
    body = response.content.decode()

    assert "Sede Pública Norte" in body
    assert "Bodega Privada Secreta" not in body
    assert "91.75" not in body
    assert "11.25" not in body
    assert "7.50" not in body
    assert "SECRET-A-99" not in body
    assert "PRIVATE-B-12" not in body


@override_settings(VINOVA_PUBLIC_PARTS_CATALOG_ENABLED=True)
def test_public_catalog_filters_are_validated_and_clearable(client, public_catalog_data):
    response = client.get(
        reverse("parts:catalog"),
        {"q": "premium", "category": "filtros-publicos", "item_type": "filter", "sort": "price_asc"},
    )

    assert response.status_code == 200
    assert list(response.context["items"]) == [public_catalog_data["published"]]
    assert response.context["has_active_filters"] is True
    assert b"Limpiar filtros" in response.content

    invalid = client.get(reverse("parts:catalog"), {"item_type": "<script>alert(1)</script>"})
    assert invalid.status_code == 200
    assert list(invalid.context["items"]) == []
    assert b"<script>alert(1)</script>" not in invalid.content


def test_public_catalog_flag_hides_route_and_navigation(client, public_catalog_data):
    with override_settings(VINOVA_PUBLIC_PARTS_CATALOG_ENABLED=False):
        assert client.get(reverse("parts:catalog")).status_code == 404
        public_page = client.get(reverse("vehicles:catalog"))
        assert b">Repuestos</a>" not in public_page.content

    with override_settings(VINOVA_PUBLIC_PARTS_CATALOG_ENABLED=True):
        public_page = client.get(reverse("vehicles:catalog"))
        assert b'href="/repuestos/"' in public_page.content
