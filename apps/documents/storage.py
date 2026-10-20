"""ES: Este módulo adapta almacenamiento y ciclo de vida de archivos para el dominio de documentos.

EN: This module adapts storage and file lifecycle behavior for the documents domain.

Contexto existente / Existing context:
Almacenamiento privado local o S3-compatible para documentos sensibles.
"""

from __future__ import annotations

import importlib.util
import logging

from django.conf import settings
from django.core.files.storage import FileSystemStorage, Storage
from django.utils.deconstruct import deconstructible

logger = logging.getLogger(__name__)


def _local_backend():
    return FileSystemStorage(location=settings.PRIVATE_STORAGE_ROOT, base_url=None)


def _s3_credentials() -> tuple[str, str, str, str]:
    return (
        settings.S3_ENDPOINT_URL,
        settings.S3_ACCESS_KEY_ID,
        settings.S3_SECRET_ACCESS_KEY,
        settings.S3_BUCKET_NAME,
    )


def s3_sdk_available() -> bool:
    return importlib.util.find_spec("boto3") is not None and importlib.util.find_spec("storages") is not None


def build_private_backend():
    """Resuelve el backend; una configuración incompleta degrada a local."""
    backend = getattr(settings, "PRIVATE_STORAGE_BACKEND", "local")
    if backend != "s3":
        return _local_backend()
    if not all(_s3_credentials()):
        logger.warning("PRIVATE_STORAGE_BACKEND=s3 sin configuración S3 completa; se usa almacenamiento local.")
        return _local_backend()
    if not s3_sdk_available():
        logger.warning("PRIVATE_STORAGE_BACKEND=s3 pero boto3/django-storages no están instalados; se usa almacenamiento local.")
        return _local_backend()

    from botocore.config import Config
    from storages.backends.s3 import S3Storage

    client_config = Config(
        connect_timeout=settings.S3_CONNECT_TIMEOUT_SECONDS,
        read_timeout=settings.S3_READ_TIMEOUT_SECONDS,
        retries={"max_attempts": 3, "mode": "standard"},
        signature_version="s3v4",
        s3={"addressing_style": settings.S3_ADDRESSING_STYLE},
    )
    return S3Storage(
        access_key=settings.S3_ACCESS_KEY_ID,
        secret_key=settings.S3_SECRET_ACCESS_KEY,
        bucket_name=settings.S3_BUCKET_NAME,
        endpoint_url=settings.S3_ENDPOINT_URL,
        region_name=settings.S3_REGION_NAME,
        location=settings.S3_PRIVATE_PREFIX,
        default_acl=None,
        file_overwrite=False,
        querystring_auth=True,
        querystring_expire=settings.S3_SIGNED_URL_EXPIRE_SECONDS,
        custom_domain=None,
        object_parameters={"ServerSideEncryption": "AES256"},
        client_config=client_config,
    )


def private_storage_health_check() -> tuple[bool, str]:
    """Comprueba acceso al bucket sin escribir ni filtrar detalles sensibles."""
    backend = getattr(settings, "PRIVATE_STORAGE_BACKEND", "local")
    if backend == "local":
        return True, "local"
    if backend != "s3":
        return False, "unsupported_backend"
    if not all(_s3_credentials()):
        return False, "missing_credentials"
    if not s3_sdk_available():
        return False, "sdk_unavailable"
    try:
        build_private_backend().exists(".vinova-healthcheck")
    except Exception as exc:  # noqa: BLE001 - el healthcheck solo publica la clase
        return False, exc.__class__.__name__
    return True, "ok"


@deconstructible
class PrivateMediaStorage(Storage):
    """Storage delegado y estable para migraciones de Django."""

    def __init__(self, location=None, base_url=None):
        # Los parámetros se conservan por compatibilidad con migraciones previas.
        self.location = location or settings.PRIVATE_STORAGE_ROOT
        self.base_url = base_url
        self._backend = None
        self._signature = None

    def _configuration_signature(self):
        return (
            getattr(settings, "PRIVATE_STORAGE_BACKEND", "local"),
            str(getattr(settings, "PRIVATE_STORAGE_ROOT", "")),
            getattr(settings, "S3_ENDPOINT_URL", ""),
            getattr(settings, "S3_ACCESS_KEY_ID", ""),
            getattr(settings, "S3_SECRET_ACCESS_KEY", ""),
            getattr(settings, "S3_BUCKET_NAME", ""),
            getattr(settings, "S3_REGION_NAME", ""),
            getattr(settings, "S3_ADDRESSING_STYLE", ""),
            getattr(settings, "S3_PRIVATE_PREFIX", ""),
            getattr(settings, "S3_SIGNED_URL_EXPIRE_SECONDS", 0),
            getattr(settings, "S3_CONNECT_TIMEOUT_SECONDS", 0),
            getattr(settings, "S3_READ_TIMEOUT_SECONDS", 0),
        )

    @property
    def backend(self):
        signature = self._configuration_signature()
        if self._backend is None or signature != self._signature:
            self._backend = build_private_backend()
            self._signature = signature
        return self._backend

    def reset(self):
        self._backend = None
        self._signature = None

    def _open(self, name, mode="rb"):
        return self.backend.open(name, mode)

    def _save(self, name, content):
        return self.backend._save(name, content)

    def get_available_name(self, name, max_length=None):
        return self.backend.get_available_name(name, max_length=max_length)

    def get_valid_name(self, name):
        return self.backend.get_valid_name(name)

    def generate_filename(self, filename):
        return self.backend.generate_filename(filename)

    def exists(self, name):
        return self.backend.exists(name)

    def delete(self, name):
        return self.backend.delete(name)

    def listdir(self, path):
        return self.backend.listdir(path)

    def size(self, name):
        return self.backend.size(name)

    def url(self, name):
        return self.backend.url(name)

    def path(self, name):
        return self.backend.path(name)

    def get_accessed_time(self, name):
        return self.backend.get_accessed_time(name)

    def get_created_time(self, name):
        return self.backend.get_created_time(name)

    def get_modified_time(self, name):
        return self.backend.get_modified_time(name)
