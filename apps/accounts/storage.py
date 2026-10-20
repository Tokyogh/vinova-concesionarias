"""ES: Este módulo adapta almacenamiento y ciclo de vida de archivos para el dominio de cuentas.

EN: This module adapts storage and file lifecycle behavior for the accounts domain.

Contexto existente / Existing context:
Adaptador de almacenamiento para avatares.

El backend se resuelve según ``settings.STORAGE_BACKEND``:

- ``local`` (por defecto): ``FileSystemStorage`` dentro de ``MEDIA_ROOT``.
- ``cloudinary``: solo si el SDK ``cloudinary`` está instalado y las
  credenciales ``CLOUDINARY_*`` están presentes. En cualquier otro caso se
  degrada a local con una advertencia, sin romper la subida.

Nunca se leen ni escriben secretos en el código: las credenciales provienen del
entorno (``config/settings/base.py``).
"""

from __future__ import annotations

import importlib.util
import logging

from django.conf import settings
from django.core.files.storage import FileSystemStorage, Storage
from django.utils.deconstruct import deconstructible

logger = logging.getLogger(__name__)


def _local_backend():
    return FileSystemStorage(location=settings.MEDIA_ROOT, base_url=settings.MEDIA_URL)


def _cloudinary_credentials():
    return (
        settings.CLOUDINARY_CLOUD_NAME,
        settings.CLOUDINARY_API_KEY,
        settings.CLOUDINARY_API_SECRET,
    )


def cloudinary_sdk_available() -> bool:
    return importlib.util.find_spec("cloudinary") is not None


def build_avatar_backend():
    """Devuelve la instancia de storage resuelta para avatares."""
    backend = getattr(settings, "STORAGE_BACKEND", "local")
    if backend != "cloudinary":
        return _local_backend()

    cloud_name, api_key, api_secret = _cloudinary_credentials()
    if not (cloud_name and api_key and api_secret):
        logger.warning("STORAGE_BACKEND=cloudinary sin credenciales CLOUDINARY_*; se usa almacenamiento local.")
        return _local_backend()
    if not cloudinary_sdk_available():
        logger.warning("STORAGE_BACKEND=cloudinary pero el SDK 'cloudinary' no está instalado; se usa almacenamiento local.")
        return _local_backend()

    from apps.accounts.cloudinary_avatar import CloudinaryAvatarStorage

    return CloudinaryAvatarStorage(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret)


@deconstructible
class AvatarStorage(Storage):
    """Storage delegado que resuelve el backend real en el primer uso."""

    def __init__(self):
        self._backend = None

    @property
    def backend(self):
        if self._backend is None:
            self._backend = build_avatar_backend()
        return self._backend

    def reset(self):
        self._backend = None

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


avatar_storage = AvatarStorage()


def get_avatar_storage():
    """Punto de acceso público para el backend de avatares resuelto."""
    return build_avatar_backend()


def resolved_avatar_provider():
    """Etiqueta del backend realmente efectivo (registrada en ``avatar_provider``)."""
    from django.core.files.storage import FileSystemStorage

    backend = build_avatar_backend()
    if isinstance(backend, FileSystemStorage):
        return "local"
    return "cloudinary"


def avatar_storage_health_check() -> tuple[bool, str]:
    """Comprueba el proveedor configurado sin exponer credenciales."""
    backend = getattr(settings, "STORAGE_BACKEND", "local")
    if backend == "local":
        return True, "local"
    if backend != "cloudinary":
        return False, "unsupported_backend"
    if not all(_cloudinary_credentials()):
        return False, "missing_credentials"
    if not cloudinary_sdk_available():
        return False, "sdk_unavailable"
    try:
        from cloudinary import api

        api.ping()
    except Exception as exc:  # noqa: BLE001 - el healthcheck solo publica la clase
        return False, exc.__class__.__name__
    return True, "ok"
