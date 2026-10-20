"""ES: Este módulo implementa el componente cloudinary avatar para el dominio de cuentas.

EN: This module implements the cloudinary avatar component for the accounts domain.

Contexto existente / Existing context:
Backend de avatares sobre el SDK de Cloudinary.

Solo se instancia cuando ``STORAGE_BACKEND=cloudinary``, las credenciales están
presentes y el paquete ``cloudinary`` está instalado (ver
``apps/accounts/storage.py``). El proveedor externo se usa exclusivamente para
avatares; los documentos privados permanecen en el almacenamiento local.
"""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.files.storage import Storage


class CloudinaryAvatarStorage(Storage):
    """ES: Agrupa el componente «cloudinary avatar storage» del dominio de cuentas y sus reglas relacionadas.

    EN: Groups the «cloudinary avatar storage» component and its related rules in the accounts domain.
    """

    def __init__(self, cloud_name, api_key, api_secret, folder="vinova/avatars"):
        import cloudinary

        cloudinary.config(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret, secure=True)
        self.folder = folder

    @staticmethod
    def _public_id(name):
        return Path(name).with_suffix("").as_posix()

    def _full_public_id(self, name):
        return f"{self.folder}/{self._public_id(name)}"

    def get_available_name(self, name, max_length=None):
        """El public_id es determinista y la subida usa overwrite=True."""
        return str(name).replace("\\", "/")

    def _save(self, name, content):
        from cloudinary import uploader

        result = uploader.upload(
            content,
            public_id=self._full_public_id(name),
            overwrite=True,
            resource_type="image",
            invalidate=True,
        )
        return result["public_id"]

    def _open(self, name, mode="rb"):
        import urllib.request

        from django.core.files.base import File

        timeout = getattr(settings, "CLOUDINARY_HTTP_TIMEOUT_SECONDS", 15)
        return File(urllib.request.urlopen(self.url(name), timeout=timeout))  # noqa: S310

    def url(self, name):
        from cloudinary.utils import cloudinary_url

        url, _ = cloudinary_url(name, secure=True, resource_type="image")
        return url

    def exists(self, name):
        from cloudinary import api
        from cloudinary.exceptions import NotFound

        try:
            api.resource(name, resource_type="image")
        except NotFound:
            return False
        return True

    def delete(self, name):
        from cloudinary import uploader

        uploader.destroy(name, resource_type="image", invalidate=True)

    def size(self, name):
        from cloudinary import api

        return api.resource(name, resource_type="image")["bytes"]

    def path(self, name):
        raise NotImplementedError("Cloudinary no expone rutas del sistema de archivos.")
