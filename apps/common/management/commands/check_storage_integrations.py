"""ES: Implementa el comando administrativo «check storage integrations» para infraestructura compartida.

EN: Implements the «check storage integrations» management command for common.

Contexto existente / Existing context:
Django management command for check storage integrations.
"""

from __future__ import annotations

import base64
import uuid

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError

from apps.accounts.storage import avatar_storage_health_check, build_avatar_backend
from apps.documents.storage import PrivateMediaStorage, private_storage_health_check

_ONE_PIXEL_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class Command(BaseCommand):
    """ES: Agrupa el componente «command» del dominio de infraestructura compartida y sus reglas relacionadas.

    EN: Groups the «command» component and its related rules in the common domain.
    """

    help = "Comprueba los proveedores de almacenamiento sin mostrar secretos."

    def add_arguments(self, parser):
        parser.add_argument(
            "--live",
            action="store_true",
            help="Ejecuta un ciclo temporal save/open/url/delete en los proveedores configurados.",
        )

    def _live_avatar_cycle(self):
        storage = build_avatar_backend()
        name = storage.save(f"smoke/{uuid.uuid4().hex}.png", ContentFile(_ONE_PIXEL_PNG))
        try:
            if not storage.exists(name):
                raise RuntimeError("stored_object_not_found")
            storage.url(name)
        finally:
            storage.delete(name)

    def _live_private_cycle(self):
        storage = PrivateMediaStorage()
        payload = b"vinova-storage-smoke"
        name = storage.save(f"smoke/{uuid.uuid4().hex}.txt", ContentFile(payload))
        try:
            with storage.open(name, "rb") as handle:
                if handle.read() != payload:
                    raise RuntimeError("stored_content_mismatch")
            storage.url(name)
        finally:
            storage.delete(name)

    def handle(self, *args, **options):
        checks = {
            "avatar": avatar_storage_health_check(),
            "private": private_storage_health_check(),
        }
        failures = [name for name, (ok, _) in checks.items() if not ok]
        for name, (ok, detail) in checks.items():
            label = self.style.SUCCESS("OK") if ok else self.style.ERROR("ERROR")
            self.stdout.write(f"[{label}] {name}: {detail}")
        if failures:
            raise CommandError(f"Storage no disponible: {', '.join(failures)}")

        if not options["live"]:
            self.stdout.write("Use --live para ejecutar el ciclo temporal de escritura y borrado.")
            return
        try:
            self._live_avatar_cycle()
            self._live_private_cycle()
        except Exception as exc:  # noqa: BLE001 - no mostrar mensajes potencialmente sensibles del proveedor
            raise CommandError(f"Falló el ciclo live de storage ({exc.__class__.__name__}).") from None
        self.stdout.write(self.style.SUCCESS("Ciclos live de avatar y documentos privados completados."))
