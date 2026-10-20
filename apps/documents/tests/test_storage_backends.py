"""ES: Este módulo especifica regresiones ejecutables para el dominio de documentos.

EN: This module specifies executable regressions for the documents domain.

Contexto existente / Existing context:
Regression coverage for storage backends in the documents domain.
"""

from __future__ import annotations

import sys
import types

import pytest
from django.core.exceptions import SuspiciousFileOperation
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage, Storage

from apps.documents.storage import PrivateMediaStorage, build_private_backend, private_storage_health_check
from apps.common.release_checks import check_storage_layout


def _s3_settings(settings):
    settings.PRIVATE_STORAGE_BACKEND = "s3"
    settings.S3_ENDPOINT_URL = "https://objects.example.test"
    settings.S3_ACCESS_KEY_ID = "access-id"
    settings.S3_SECRET_ACCESS_KEY = "super-secret-value"
    settings.S3_BUCKET_NAME = "vinova-private"
    settings.S3_REGION_NAME = "auto"
    settings.S3_ADDRESSING_STYLE = "path"
    settings.S3_PRIVATE_PREFIX = "vinova/private"
    settings.S3_SIGNED_URL_EXPIRE_SECONDS = 300
    settings.S3_CONNECT_TIMEOUT_SECONDS = 4
    settings.S3_READ_TIMEOUT_SECONDS = 12


def _install_fake_s3(monkeypatch):
    class FakeConfig:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

    class FakeS3Storage(Storage):
        objects = {}
        init_kwargs = None

        def __init__(self, **kwargs):
            type(self).init_kwargs = kwargs

        def _save(self, name, content):
            type(self).objects[name] = content.read()
            return name

        def _open(self, name, mode="rb"):
            return ContentFile(type(self).objects[name], name=name)

        def exists(self, name):
            return name in type(self).objects

        def delete(self, name):
            type(self).objects.pop(name, None)

        def url(self, name):
            return f"https://signed.example.test/{name}?X-Amz-Signature=fake"

    boto3 = types.ModuleType("boto3")
    botocore = types.ModuleType("botocore")
    botocore_config = types.ModuleType("botocore.config")
    botocore_config.Config = FakeConfig
    storages = types.ModuleType("storages")
    backends = types.ModuleType("storages.backends")
    s3 = types.ModuleType("storages.backends.s3")
    s3.S3Storage = FakeS3Storage
    monkeypatch.setitem(sys.modules, "boto3", boto3)
    monkeypatch.setitem(sys.modules, "botocore", botocore)
    monkeypatch.setitem(sys.modules, "botocore.config", botocore_config)
    monkeypatch.setitem(sys.modules, "storages", storages)
    monkeypatch.setitem(sys.modules, "storages.backends", backends)
    monkeypatch.setitem(sys.modules, "storages.backends.s3", s3)
    monkeypatch.setattr("apps.documents.storage.s3_sdk_available", lambda: True)
    return FakeS3Storage


def test_private_local_storage_save_open_delete(settings, tmp_path):
    settings.PRIVATE_STORAGE_BACKEND = "local"
    settings.PRIVATE_STORAGE_ROOT = tmp_path / "private"
    storage = PrivateMediaStorage()

    name = storage.save("documents/test.txt", ContentFile(b"private"))

    assert isinstance(storage.backend, FileSystemStorage)
    with storage.open(name, "rb") as handle:
        assert handle.read() == b"private"
    storage.delete(name)
    assert not storage.exists(name)


def test_private_local_storage_rejects_path_traversal(settings, tmp_path):
    settings.PRIVATE_STORAGE_BACKEND = "local"
    settings.PRIVATE_STORAGE_ROOT = tmp_path / "private"
    storage = PrivateMediaStorage()

    with pytest.raises(SuspiciousFileOperation):
        storage.save("../escape.txt", ContentFile(b"private"))

    assert not (tmp_path / "escape.txt").exists()


def test_s3_storage_is_private_signed_and_supports_lifecycle(settings, monkeypatch):
    _s3_settings(settings)
    fake = _install_fake_s3(monkeypatch)
    storage = PrivateMediaStorage()

    name = storage.save("documents/test.txt", ContentFile(b"private"))

    with storage.open(name, "rb") as handle:
        assert handle.read() == b"private"
    assert "X-Amz-Signature" in storage.url(name)
    assert fake.init_kwargs["default_acl"] is None
    assert fake.init_kwargs["querystring_auth"] is True
    assert fake.init_kwargs["querystring_expire"] == 300
    assert fake.init_kwargs["object_parameters"] == {"ServerSideEncryption": "AES256"}
    assert fake.init_kwargs["client_config"].kwargs["connect_timeout"] == 4
    assert fake.init_kwargs["client_config"].kwargs["signature_version"] == "s3v4"
    assert fake.init_kwargs["client_config"].kwargs["s3"] == {"addressing_style": "path"}
    storage.delete(name)
    assert not storage.exists(name)


def test_s3_missing_credentials_falls_back_without_leaking_secret(settings, caplog):
    _s3_settings(settings)
    settings.S3_BUCKET_NAME = ""

    with caplog.at_level("WARNING"):
        backend = build_private_backend()

    assert isinstance(backend, FileSystemStorage)
    assert "super-secret-value" not in caplog.text


def test_s3_health_reports_provider_failure_by_class_only(settings, monkeypatch):
    _s3_settings(settings)
    _install_fake_s3(monkeypatch)

    class ProviderUnavailable(Exception):
        pass

    class FailingStorage:
        def exists(self, name):
            raise ProviderUnavailable("super-secret-value")

    monkeypatch.setattr("apps.documents.storage.build_private_backend", lambda: FailingStorage())

    assert private_storage_health_check() == (False, "ProviderUnavailable")


def test_s3_backend_builder_never_embeds_secret_in_repr(settings, monkeypatch):
    _s3_settings(settings)
    _install_fake_s3(monkeypatch)

    backend = build_private_backend()

    assert "super-secret-value" not in repr(backend)


def test_release_check_rejects_incomplete_s3_without_leaking_secret(settings):
    _s3_settings(settings)
    settings.S3_BUCKET_NAME = ""

    result = check_storage_layout()[0]

    assert result.level == "error"
    assert "S3_BUCKET_NAME" in result.message
    assert "super-secret-value" not in result.message
