"""ES: Este módulo especifica regresiones ejecutables para el dominio de infraestructura compartida.

EN: This module specifies executable regressions for the common domain.

Contexto existente / Existing context:
Regression coverage for release stabilization v023 in the common domain.
"""

from __future__ import annotations

import re
from io import StringIO
from pathlib import Path

import pytest
import yaml
from django.conf import settings
from django.core.management import call_command
from django.http import HttpResponse
from django.test import RequestFactory
from django.utils import timezone
from rest_framework.request import Request

from apps.accounts.api.serializers import UserSerializer
from apps.accounts.api.views import UserViewSet
from apps.accounts.models import Role, User, UserRole
from apps.common.release_checks import run_static_release_checks
from apps.security_center.middleware import SecurityHeadersMiddleware
from apps.vehicles.models import Vehicle, VehicleBrand, VehicleMedia, VehicleModel, VehicleResource
from apps.vehicles.selectors import public_vehicle_queryset
from scripts.build_release_zip import should_include


def test_release_readiness_static_checks_have_no_failures():
    failures = [result for result in run_static_release_checks() if result.level != "ok"]
    assert failures == []


def test_release_dependency_installation_is_hash_locked():
    """Exige lock con hashes. / Require a hash-locked production dependency set."""

    root = Path(settings.BASE_DIR)
    dockerfile = (root / "Dockerfile").read_text(encoding="utf-8")
    lock = (root / "requirements/production.lock").read_text(encoding="utf-8")

    assert "ARG REQUIREMENTS_FILE=production.lock" in dockerfile
    assert "pip wheel --require-hashes" in dockerfile
    assert "--hash=sha256:" in lock
    assert "-r production.txt" not in lock


def test_docker_context_excludes_lite_and_local_tls_secrets():
    """Evita datos ajenos/secretos en imagen. / Keep foreign data and secrets out of images."""

    dockerignore = (Path(settings.BASE_DIR) / ".dockerignore").read_text(encoding="utf-8").splitlines()

    assert "web_carros" in dockerignore
    assert "docker/nginx/certs/*" in dockerignore
    assert "!docker/nginx/certs/.gitkeep" in dockerignore


def test_trivy_gate_uses_a_digest_pinned_scanner():
    """Fija el escáner del gate. / Pin the gate scanner itself."""

    root = Path(settings.BASE_DIR)
    expected = "aquasec/trivy:0.76.0@sha256:2416d1f74045b57274df1a340eee6b510cacd73c66a6ccb8da092b117eb7d222"

    for script_path in ("scripts/validate-nginx-security.ps1", "scripts/validate-nginx-security.sh"):
        assert expected in (root / script_path).read_text(encoding="utf-8")


def test_nginx_image_pins_fixed_alpine_revisions():
    """Conserva los parches reproducibles. / Keep reproducible security revisions."""

    dockerfile = (Path(settings.BASE_DIR) / "docker/nginx/Dockerfile").read_text(encoding="utf-8")

    assert "@sha256:adf5042a17f4ecdd200c595fa9ffd1be37efb18f89a830bd1a00e4ab4d59d42c" in dockerfile
    for package in ("libexpat=2.8.5-r0", "pcre2=10.49-r0", "tiff=4.7.2-r0", "zlib=1.3.2-r1"):
        assert package in dockerfile


@pytest.mark.parametrize(
    ("compose_filename", "service_names"),
    [
        ("docker-compose.yml", {"db", "redis", "mailpit", "minio"}),
        ("docker-compose.prod.yml", {"db", "redis"}),
        ("docker-compose.qa.yml", {"qa_db", "qa_redis"}),
        ("docker-compose.qa-cli.yml", {"qa_db", "qa_redis"}),
    ],
)
def test_third_party_container_images_are_digest_pinned(compose_filename: str, service_names: set[str]):
    """Impide tags externos mutables. / Prevent mutable third-party image tags."""

    compose = yaml.safe_load((Path(settings.BASE_DIR) / compose_filename).read_text(encoding="utf-8"))

    for service_name in service_names:
        image = compose["services"][service_name]["image"]
        assert re.search(r"@sha256:[0-9a-f]{64}$", image)


@pytest.mark.django_db
def test_release_readiness_management_command_runs_in_strict_mode():
    output = StringIO()
    call_command("check_release_readiness", "--strict", stdout=output)
    assert "Release listo a nivel estático" in output.getvalue()


def test_security_headers_do_not_require_inline_scripts():
    request = RequestFactory().get("/")
    response = SecurityHeadersMiddleware(lambda _request: HttpResponse("ok"))(request)
    csp = response["Content-Security-Policy"]

    script_directive = next(part.strip() for part in csp.split(";") if part.strip().startswith("script-src"))
    assert "'unsafe-inline'" not in script_directive
    assert "https://unpkg.com" in script_directive
    assert "object-src 'none'" in csp
    assert "frame-ancestors 'none'" in csp
    assert response["Cross-Origin-Resource-Policy"] == "same-site"
    assert response["X-Permitted-Cross-Domain-Policies"] == "none"


def test_base_templates_keep_accessibility_and_pinned_scripts():
    root = Path(settings.BASE_DIR)
    internal = (root / "templates/base/base.html").read_text(encoding="utf-8")
    public = (root / "templates/base/public.html").read_text(encoding="utf-8")
    modal = (root / "templates/vehicles/partials/vehicle_detail_modal.html").read_text(encoding="utf-8")

    for template in (internal, public):
        assert 'href="#main-content"' in template
        assert 'id="main-content"' in template
        assert "alpinejs" not in template.lower()
        assert "vendor/htmx/htmx.min.js" in template
        assert "https://unpkg.com/htmx" not in template

    assert 'role="dialog"' in modal
    assert 'aria-modal="true"' in modal
    assert 'role="tablist"' in modal
    assert "x-data" not in modal


def test_modal_actions_use_one_canonical_component_rule_without_legacy_css():
    root = Path(settings.BASE_DIR)
    components = (root / "static/css/ui/components/modal.css").read_text(encoding="utf-8")
    pages = (root / "static/css/ui/pages.css").read_text(encoding="utf-8")
    head_assets = (root / "templates/components/head_assets.html").read_text(encoding="utf-8")

    assert components.count(".modal-commercial-actions {") == 1
    assert "display: flex" in components.split(".modal-commercial-actions {", maxsplit=1)[1].split("}", maxsplit=1)[0]
    assert ".modal-commercial-actions {" not in pages
    assert "css/vinova.css" not in head_assets


@pytest.mark.django_db
def test_user_api_serializer_reuses_active_role_prefetch(django_assert_num_queries):
    user = User.objects.create_user(username="api-user", email="api-user@example.com", password="test-password")
    role = Role.objects.create(code="api-role", name="API Role", level=40)
    UserRole.objects.create(user=user, role=role, is_active=True)

    accessor = User.objects.create_superuser(
        username="api-accessor", email="api-accessor@example.com", password="test-password"
    )
    factory = RequestFactory()
    drf_request = Request(factory.get("/"))
    drf_request.user = accessor
    drf_request.api_client = None

    view = UserViewSet()
    view.request = drf_request
    view.action = "retrieve"
    view.kwargs = {}
    view.format_kwarg = None

    instance = view.get_queryset().get(pk=user.pk)
    with django_assert_num_queries(0):
        payload = UserSerializer(instance).data

    assert payload["roles"][0]["role"]["code"] == "api-role"


@pytest.mark.django_db
def test_vehicle_media_properties_reuse_catalog_prefetch(django_assert_num_queries):
    brand = VehicleBrand.objects.create(name="Marca Release")
    model = VehicleModel.objects.create(brand=brand, name="Modelo Release")
    vehicle = Vehicle.objects.create(
        brand=brand,
        model=model,
        year=2026,
        public_slug="marca-release-modelo-release-2026",
        published_at=timezone.now(),
    )
    hero_resource = VehicleResource.objects.create(
        title="Imagen principal",
        resource_type=VehicleResource.ResourceType.IMAGE,
        file="vehicles/resources/release-hero.jpg",
    )
    model_resource = VehicleResource.objects.create(
        title="Modelo 3D",
        resource_type=VehicleResource.ResourceType.MODEL_3D,
        file="vehicles/resources/release-model.glb",
    )
    hero = VehicleMedia.objects.create(
        vehicle=vehicle,
        resource=hero_resource,
        media_type=VehicleMedia.MediaType.HERO,
        order=1,
    )
    model_3d = VehicleMedia.objects.create(
        vehicle=vehicle,
        resource=model_resource,
        media_type=VehicleMedia.MediaType.MODEL_3D,
        order=2,
    )

    instance = public_vehicle_queryset().get(pk=vehicle.pk)
    with django_assert_num_queries(0):
        selected_hero = instance.hero_media
        selected_model = instance.active_model_3d

    assert selected_hero.pk == hero.pk
    assert selected_model.pk == model_3d.pk


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (Path(".env"), False),
        (Path(".env.example"), True),
        (Path("private/customer/document.pdf"), False),
        (Path("private/.gitkeep"), True),
        (Path("media/vehicle/photo.jpg"), False),
        (Path("docker/nginx/certs/privkey.pem"), False),
        (Path("apps/common/release_checks.py"), True),
        (Path("__pycache__/module.pyc"), False),
    ],
)
def test_release_zip_exclusion_policy(path: Path, expected: bool):
    assert should_include(path) is expected


@pytest.mark.parametrize("compose_filename", ["docker-compose.yml", "docker-compose.prod.yml"])
def test_web_healthcheck_expands_configured_host(compose_filename: str):
    compose = yaml.safe_load((Path(settings.BASE_DIR) / compose_filename).read_text(encoding="utf-8"))
    command = compose["services"]["web"]["healthcheck"]["test"][1]

    assert "--header 'Host: $${VINOVA_HEALTHCHECK_HOST" not in command
    assert "--header Host:$${VINOVA_HEALTHCHECK_HOST" in command


def test_internal_shell_uses_consolidated_mobile_inventory_layout():
    root = Path(settings.BASE_DIR)
    css = (root / "static/css/ui/responsive/mobile.css").read_text(encoding="utf-8")
    inventory = (root / "templates/inventory/internal/item_list.html").read_text(encoding="utf-8")

    assert ".mobile-card-table td::before" in css
    assert "content: attr(data-label)" in css
    assert "min-width:720px" not in css
    assert "mobile-card-table inventory-item-table" in inventory
    assert 'data-label="Artículo"' in inventory
