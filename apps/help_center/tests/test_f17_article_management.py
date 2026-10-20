"""ES: Regresiones F17 para gestión, publicación y versiones de ayuda.

EN: F17 regressions for help management, publication, and versions.
"""

import pytest
from django.urls import reverse

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.audit.models import AuditLog
from apps.help_center.models import HelpArticle, HelpCategory, UserHelpPreference


def _grant(user, *codes):
    role = Role.objects.create(code=f"help-f17-{user.username}", name="Ayuda F17")
    permissions = [
        PermissionCode.objects.get_or_create(
            module=code.split(".", 1)[0], code=code, defaults={"name": code}
        )[0]
        for code in codes
    ]
    role.permissions.set(permissions)
    UserRole.objects.create(user=user, role=role)


@pytest.fixture
def help_category(db):
    return HelpCategory.objects.create(name="Operación F17", slug="operacion-f17")


@pytest.fixture
def help_manager(django_user_model):
    user = django_user_model.objects.create_user(username="help-manager-f17", password="x")
    _grant(user, "help.view", "help.manage", "vehicles.view")
    return user


def _article_data(category, **overrides):
    data = {
        "category": category.pk,
        "title": "Guía operativa F17",
        "slug": "guia-operativa-f17",
        "summary": "Resumen controlado",
        "content": "Contenido inicial seguro.",
        "article_type": "guide",
        "route_name": "",
        "permission_code": "",
        "role_codes": "",
        "keywords": "operación, pruebas",
        "estimated_minutes": 5,
        "order": 10,
        "is_featured": "",
        "is_published": "on",
        "change_note": "Creación inicial controlada.",
    }
    data.update(overrides)
    return data


@pytest.mark.django_db
def test_help_manage_requires_specific_permission_not_staff_flag(
    client, django_user_model
):
    user = django_user_model.objects.create_user(username="staff-without-help-manage", password="x", is_staff=True)
    _grant(user, "help.view")
    client.force_login(user)

    response = client.get(reverse("help_center:manage_articles"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_manager_creates_article_first_version_and_audit(
    client, help_manager, help_category
):
    client.force_login(help_manager)

    response = client.post(reverse("help_center:manage_create"), _article_data(help_category))

    article = HelpArticle.objects.get(slug="guia-operativa-f17")
    assert response.status_code == 302
    assert response.url == reverse("help_center:manage_preview", kwargs={"pk": article.pk})
    version = article.versions.get()
    assert version.version == 1
    assert version.created_by == help_manager
    assert AuditLog.objects.filter(action="help.article.create", object_id=str(article.pk)).exists()


@pytest.mark.django_db
def test_preview_escapes_html_and_draft_is_hidden_from_reader(
    client, django_user_model, help_manager, help_category
):
    article = HelpArticle.objects.create(
        category=help_category,
        title="Borrador seguro",
        slug="borrador-seguro",
        content="<script>alert('x')</script>",
        is_published=False,
    )
    reader = django_user_model.objects.create_user(
        username="help-reader-f17", email="help-reader-f17@example.com", password="x"
    )
    _grant(reader, "help.view")

    client.force_login(help_manager)
    preview = client.get(reverse("help_center:manage_preview", kwargs={"pk": article.pk}))
    assert preview.status_code == 200
    assert b"<script>" not in preview.content
    assert b"&lt;script&gt;" in preview.content

    client.force_login(reader)
    detail = client.get(reverse("help_center:article", kwargs={"slug": article.slug}))
    assert detail.status_code == 404


@pytest.mark.django_db
def test_update_publish_cycle_and_restore_keep_immutable_history(
    client, help_manager, help_category
):
    client.force_login(help_manager)
    client.post(reverse("help_center:manage_create"), _article_data(help_category))
    article = HelpArticle.objects.get(slug="guia-operativa-f17")
    first = article.versions.get(version=1)

    updated_data = _article_data(
        help_category,
        content="Contenido actualizado.",
        change_note="Actualización funcional.",
    )
    updated = client.post(reverse("help_center:manage_edit", kwargs={"pk": article.pk}), updated_data)
    unpublished = client.post(
        reverse("help_center:manage_publication", kwargs={"pk": article.pk, "action": "unpublish"})
    )
    restored = client.post(
        reverse(
            "help_center:manage_restore",
            kwargs={"pk": article.pk, "version_pk": first.pk},
        )
    )

    article.refresh_from_db()
    assert updated.status_code == 302
    assert unpublished.status_code == 302
    assert restored.status_code == 302
    assert article.content == "Contenido inicial seguro."
    assert article.is_published is True
    assert list(article.versions.values_list("version", flat=True)) == [4, 3, 2, 1]
    assert article.versions.get(version=4).change_note == "Restauración de la versión 1"
    assert AuditLog.objects.filter(action="help.article.restore", object_id=str(article.pk)).exists()


@pytest.mark.django_db
def test_contextual_article_changes_appear_without_deployment(
    client, help_manager, help_category
):
    article = HelpArticle.objects.create(
        category=help_category,
        title="Ayuda dinámica F17",
        slug="ayuda-dinamica-f17",
        summary="Consejo contextual actualizado sin despliegue.",
        content="Contenido contextual.",
        route_name="vehicles_internal:list",
        permission_code="vehicles.view",
        is_published=True,
    )
    UserHelpPreference.objects.create(user=help_manager, training_mode=True)
    client.force_login(help_manager)

    response = client.get(reverse("vehicles_internal:list"))

    assert response.status_code == 200
    assert article.summary.encode() in response.content
