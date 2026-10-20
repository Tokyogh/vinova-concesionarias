"""ES: Este módulo especifica regresiones ejecutables para el dominio de cuentas.

EN: This module specifies executable regressions for the accounts domain.

Contexto existente / Existing context:
Regression coverage for avatar in the accounts domain.
"""

import io
import sys
import types

import pytest
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from PIL import Image

from apps.accounts.storage import (
    AvatarStorage,
    avatar_storage,
    avatar_storage_health_check,
    build_avatar_backend,
    resolved_avatar_provider,
)
from apps.common.validators import validate_avatar_image


def png_bytes(width=256, height=256, color=(12, 32, 64)):
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), color).save(buffer, format="PNG")
    return buffer.getvalue()


def gif_bytes(width=128, height=128):
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (200, 10, 10)).save(buffer, format="GIF")
    return buffer.getvalue()


def png_upload(name="foto.png", content=None, content_type="image/png"):
    return SimpleUploadedFile(name, content if content is not None else png_bytes(), content_type=content_type)


@pytest.fixture(autouse=True)
def _reset_avatar_storage():
    avatar_storage.reset()
    yield
    avatar_storage.reset()


@pytest.fixture
def media_root(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    avatar_storage.reset()
    return tmp_path


@pytest.mark.django_db
def test_valid_png_passes_avatar_validator():
    validate_avatar_image(png_upload())


def test_fake_image_rejected():
    with pytest.raises(ValidationError):
        validate_avatar_image(png_upload(content=b"no es una imagen"))


def test_disallowed_extension_rejected():
    with pytest.raises(ValidationError):
        validate_avatar_image(png_upload(name="foto.gif", content=gif_bytes()))


def test_real_gif_with_image_extension_rejected():
    with pytest.raises(ValidationError):
        validate_avatar_image(png_upload(name="foto.png", content=gif_bytes()))


def test_oversized_image_rejected(settings):
    settings.VINOVA_AVATAR_MAX_MB = 1
    oversized = png_bytes() + b"\x00" * (1024 * 1024)
    with pytest.raises(ValidationError):
        validate_avatar_image(png_upload(content=oversized))


def test_small_dimensions_rejected(settings):
    settings.VINOVA_AVATAR_MIN_DIMENSION = 64
    with pytest.raises(ValidationError):
        validate_avatar_image(png_upload(content=png_bytes(width=32, height=32)))


def test_large_dimensions_rejected(settings):
    settings.VINOVA_AVATAR_MAX_DIMENSION = 128
    with pytest.raises(ValidationError):
        validate_avatar_image(png_upload(content=png_bytes(width=512, height=512)))


@pytest.mark.django_db
def test_upload_saves_local_file_and_provider(client, django_user_model, media_root):
    user = django_user_model.objects.create_user(username="ana", email="ana@example.com", password="VinovaTest2026*")
    client.force_login(user)

    response = client.post(reverse("accounts:avatar_update"), {"avatar": png_upload()})

    assert response.status_code == 302
    user.refresh_from_db()
    assert user.avatar_provider == "local"
    assert user.avatar.name.startswith("avatars/")
    assert user.avatar.storage.exists(user.avatar.name)
    assert user.avatar_url
    assert (media_root / user.avatar.name).exists()


@pytest.mark.django_db
def test_replacement_removes_previous_file(
    client,
    django_user_model,
    media_root,
    django_capture_on_commit_callbacks,
):
    user = django_user_model.objects.create_user(username="ana", email="ana@example.com", password="VinovaTest2026*")
    client.force_login(user)

    client.post(reverse("accounts:avatar_update"), {"avatar": png_upload(content=png_bytes(color=(1, 2, 3)))})
    user.refresh_from_db()
    first_name = user.avatar.name

    with django_capture_on_commit_callbacks(execute=True):
        client.post(reverse("accounts:avatar_update"), {"avatar": png_upload(content=png_bytes(color=(9, 9, 9)))})
    user.refresh_from_db()

    assert user.avatar.name != first_name
    assert not user.avatar.storage.exists(first_name)


@pytest.mark.django_db
def test_invalid_upload_keeps_previous_avatar(client, django_user_model, media_root):
    user = django_user_model.objects.create_user(username="ana", email="ana@example.com", password="VinovaTest2026*")
    client.force_login(user)

    client.post(reverse("accounts:avatar_update"), {"avatar": png_upload()})
    user.refresh_from_db()
    original_name = user.avatar.name

    response = client.post(reverse("accounts:avatar_update"), {"avatar": png_upload(content=b"contenido falso")})

    assert response.status_code == 302
    user.refresh_from_db()
    assert user.avatar.name == original_name


@pytest.mark.django_db
def test_avatar_requires_authentication(client):
    response = client.post(reverse("accounts:avatar_update"))
    assert response.status_code == 302
    assert reverse("accounts:login") in response.url


@pytest.mark.django_db
def test_delete_avatar_removes_file(
    client,
    django_user_model,
    media_root,
    django_capture_on_commit_callbacks,
):
    user = django_user_model.objects.create_user(username="ana", email="ana@example.com", password="VinovaTest2026*")
    client.force_login(user)
    client.post(reverse("accounts:avatar_update"), {"avatar": png_upload()})
    user.refresh_from_db()
    stored = avatar_storage
    name = user.avatar.name

    with django_capture_on_commit_callbacks(execute=True):
        response = client.post(reverse("accounts:avatar_delete"))

    assert response.status_code == 302
    user.refresh_from_db()
    assert not user.avatar
    assert user.avatar_provider == "local"
    assert not stored.exists(name)


@pytest.mark.django_db
def test_failed_avatar_update_cleans_new_storage_object(client, django_user_model, media_root, monkeypatch):
    user = django_user_model.objects.create_user(username="avatar-fail", email="avatar-fail@example.com", password="x")
    client.force_login(user)
    original_save = django_user_model.save

    def fail_after_file_save(instance, *args, **kwargs):
        if "avatar" in (kwargs.get("update_fields") or ()):
            if instance.avatar and not instance.avatar._committed:
                instance.avatar.save(instance.avatar.name, instance.avatar.file, save=False)
            raise RuntimeError("database unavailable")
        return original_save(instance, *args, **kwargs)

    monkeypatch.setattr(django_user_model, "save", fail_after_file_save)
    response = client.post(reverse("accounts:avatar_update"), {"avatar": png_upload()})

    assert response.status_code == 302
    user.refresh_from_db()
    assert not user.avatar
    assert not [path for path in media_root.rglob("*") if path.is_file()]


@pytest.mark.django_db
def test_failed_avatar_delete_keeps_database_reference_and_file(client, django_user_model, media_root, monkeypatch):
    user = django_user_model.objects.create_user(
        username="avatar-delete-fail", email="avatar-delete-fail@example.com", password="x"
    )
    client.force_login(user)
    client.post(reverse("accounts:avatar_update"), {"avatar": png_upload()})
    user.refresh_from_db()
    old_name = user.avatar.name
    storage = user.avatar.storage
    original_save = django_user_model.save

    def fail_avatar_save(instance, *args, **kwargs):
        if "avatar" in (kwargs.get("update_fields") or ()):
            raise RuntimeError("database unavailable")
        return original_save(instance, *args, **kwargs)

    monkeypatch.setattr(django_user_model, "save", fail_avatar_save)
    response = client.post(reverse("accounts:avatar_delete"))

    assert response.status_code == 302
    user.refresh_from_db()
    assert user.avatar.name == old_name
    assert storage.exists(old_name)


@pytest.mark.django_db
def test_avatar_edit_only_affects_requesting_user(client, django_user_model, media_root):
    author = django_user_model.objects.create_user(username="ana", email="ana@example.com", password="VinovaTest2026*")
    other = django_user_model.objects.create_user(username="luis", email="luis@example.com", password="VinovaTest2026*")
    client.force_login(author)

    client.post(reverse("accounts:avatar_update"), {"avatar": png_upload()})

    author.refresh_from_db()
    other.refresh_from_db()
    assert author.avatar
    assert not other.avatar


@pytest.mark.django_db
def test_profile_renders_avatar_image_and_fallback(client, django_user_model, media_root):
    user = django_user_model.objects.create_user(username="ana", email="ana@example.com", password="VinovaTest2026*")
    client.force_login(user)

    fallback = client.get(reverse("accounts:profile"))
    assert "avatar-fallback" in fallback.content.decode()

    client.post(reverse("accounts:avatar_update"), {"avatar": png_upload()})
    user.refresh_from_db()

    with_avatar = client.get(reverse("accounts:profile"))
    assert user.avatar_url in with_avatar.content.decode()


@pytest.mark.django_db
def test_avatar_rendered_in_staff_and_public_navbars(client, django_user_model, media_root):
    user = django_user_model.objects.create_superuser(
        username="root", email="root@example.com", password="VinovaTest2026*"
    )
    client.force_login(user)
    client.post(reverse("accounts:avatar_update"), {"avatar": png_upload()})
    user.refresh_from_db()
    assert user.avatar_url

    staff = client.get(reverse("dashboard:staff_home"))
    assert user.avatar_url in staff.content.decode()
    assert "user-pill" in staff.content.decode()

    public = client.get(reverse("dashboard:home"))
    assert user.avatar_url in public.content.decode()


def test_cloudinary_backend_without_credentials_falls_back_to_local(settings, caplog):
    settings.STORAGE_BACKEND = "cloudinary"
    settings.CLOUDINARY_CLOUD_NAME = ""
    settings.CLOUDINARY_API_KEY = ""
    settings.CLOUDINARY_API_SECRET = ""

    with caplog.at_level("WARNING"):
        backend = build_avatar_backend()

    assert isinstance(backend, FileSystemStorage)
    assert resolved_avatar_provider() == "local"
    assert any("credenciales" in record.message for record in caplog.records)


def test_cloudinary_backend_without_sdk_falls_back_to_local(settings, monkeypatch, caplog):
    settings.STORAGE_BACKEND = "cloudinary"
    settings.CLOUDINARY_CLOUD_NAME = "demo"
    settings.CLOUDINARY_API_KEY = "key"
    settings.CLOUDINARY_API_SECRET = "secret"
    monkeypatch.setattr("apps.accounts.storage.cloudinary_sdk_available", lambda: False)

    with caplog.at_level("WARNING"):
        backend = build_avatar_backend()

    assert isinstance(backend, FileSystemStorage)
    assert any("SDK" in record.message for record in caplog.records)


def _install_fake_cloudinary():
    cloudinary = types.ModuleType("cloudinary")

    def config(**kwargs):
        config.calls.append(kwargs)

    config.calls = []
    cloudinary.config = config

    uploader = types.ModuleType("cloudinary.uploader")

    def upload(content, **kwargs):
        if upload.failure:
            raise RuntimeError("provider unavailable: super-secret-value")
        upload.calls.append(kwargs)
        public_id = kwargs["public_id"]
        upload.objects[public_id] = content.read()
        return {"public_id": public_id}

    upload.calls = []
    upload.objects = {}
    upload.failure = False
    uploader.upload = upload

    def destroy(name, **kwargs):
        if destroy.failure:
            raise RuntimeError("provider unavailable: super-secret-value")
        upload.objects.pop(name, None)
        return {"result": "ok"}

    destroy.failure = False
    uploader.destroy = destroy

    utils = types.ModuleType("cloudinary.utils")
    utils.cloudinary_url = lambda name, **kwargs: (f"https://cdn.example.com/{name}", {})

    exceptions = types.ModuleType("cloudinary.exceptions")

    class NotFound(Exception):
        pass

    exceptions.NotFound = NotFound

    api = types.ModuleType("cloudinary.api")

    def resource(name, **kwargs):
        if name not in upload.objects:
            raise NotFound(name)
        return {"bytes": len(upload.objects[name])}

    api.resource = resource
    api.ping = lambda: {"status": "ok"}

    cloudinary.uploader = uploader
    cloudinary.utils = utils
    cloudinary.exceptions = exceptions
    cloudinary.api = api

    sys.modules["cloudinary"] = cloudinary
    sys.modules["cloudinary.uploader"] = uploader
    sys.modules["cloudinary.utils"] = utils
    sys.modules["cloudinary.exceptions"] = exceptions
    sys.modules["cloudinary.api"] = api
    return cloudinary, uploader


def test_cloudinary_backend_used_when_sdk_and_credentials_present(settings, monkeypatch, media_root):
    settings.STORAGE_BACKEND = "cloudinary"
    settings.CLOUDINARY_CLOUD_NAME = "demo"
    settings.CLOUDINARY_API_KEY = "key"
    settings.CLOUDINARY_API_SECRET = "secret"
    monkeypatch.setattr("apps.accounts.storage.cloudinary_sdk_available", lambda: True)
    cloudinary, uploader = _install_fake_cloudinary()
    try:
        backend = build_avatar_backend()
        assert backend.__class__.__name__ == "CloudinaryAvatarStorage"
        assert resolved_avatar_provider() == "cloudinary"
        assert cloudinary.config.calls[0]["cloud_name"] == "demo"

        name = backend.save("avatars/2026/10/foto.png", ContentFile(png_bytes()))
        assert name == "vinova/avatars/avatars/2026/10/foto"
        assert uploader.upload.calls[0]["overwrite"] is True
        assert backend.url(name) == f"https://cdn.example.com/{name}"
        assert backend.exists(name)
        assert backend.size(name) == len(png_bytes())
        backend.delete(name)
        assert not backend.exists(name)
    finally:
        for module in (
            "cloudinary",
            "cloudinary.uploader",
            "cloudinary.utils",
            "cloudinary.exceptions",
            "cloudinary.api",
        ):
            sys.modules.pop(module, None)


def test_avatar_storage_delegates_local_operations(media_root):
    storage = AvatarStorage()
    name = storage.save("avatars/prueba.txt", ContentFile(b"datos"))

    assert storage.exists(name)
    with storage.open(name) as handle:
        assert handle.read() == b"datos"
    storage.delete(name)
    assert not storage.exists(name)


def test_cloudinary_health_probe_is_real_and_redacted(settings, monkeypatch):
    settings.STORAGE_BACKEND = "cloudinary"
    settings.CLOUDINARY_CLOUD_NAME = "demo"
    settings.CLOUDINARY_API_KEY = "key"
    settings.CLOUDINARY_API_SECRET = "super-secret-value"
    monkeypatch.setattr("apps.accounts.storage.cloudinary_sdk_available", lambda: True)
    _install_fake_cloudinary()

    assert avatar_storage_health_check() == (True, "ok")


@pytest.mark.django_db
def test_cloudinary_failure_is_controlled_and_keeps_previous_avatar(
    client, django_user_model, media_root, settings, monkeypatch
):
    user = django_user_model.objects.create_user(username="ana", email="ana@example.com", password="VinovaTest2026*")
    client.force_login(user)
    client.post(reverse("accounts:avatar_update"), {"avatar": png_upload()})
    user.refresh_from_db()
    original_name = user.avatar.name
    assert (media_root / original_name).exists()

    settings.STORAGE_BACKEND = "cloudinary"
    settings.CLOUDINARY_CLOUD_NAME = "demo"
    settings.CLOUDINARY_API_KEY = "key"
    settings.CLOUDINARY_API_SECRET = "super-secret-value"
    monkeypatch.setattr("apps.accounts.storage.cloudinary_sdk_available", lambda: True)
    _, uploader = _install_fake_cloudinary()
    uploader.upload.failure = True
    avatar_storage.reset()

    response = client.post(
        reverse("accounts:avatar_update"), {"avatar": png_upload(content=png_bytes(color=(3, 4, 5)))}
    )

    assert response.status_code == 302
    user.refresh_from_db()
    assert user.avatar.name == original_name
    assert (media_root / original_name).exists()
