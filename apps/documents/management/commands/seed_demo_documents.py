"""ES: Implementa el comando administrativo «seed demo documents» para documentos.

EN: Implements the «seed demo documents» management command for documents.

Contexto existente / Existing context:
Django management command for seed demo documents.
"""

from __future__ import annotations

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.branches.models import Branch
from apps.customers.models import Customer
from apps.documents.models import DocumentCategory, PrivateDocument, ReusableAsset
from apps.documents.services import _uploaded_file_metadata
from apps.sales.models import SaleRecord
from apps.vehicles.models import Vehicle, VehicleMedia, VehicleResource


class Command(BaseCommand):
    """ES: Agrupa el componente «command» del dominio de documentos y sus reglas relacionadas. Además, conserva atomicidad y bloqueos explícitos.

    EN: Groups the «command» component and its related rules in the documents domain. It also preserves atomicity and explicit locking.
    """

    help = "Crea documentos, recursos y multimedia demo para validar uploads protegidos y públicos."

    @transaction.atomic
    def handle(self, *args, **options):
        """ES: Orquesta «seed demo documents» con fallos controlados para documentos.

        EN: Orchestrates «seed demo documents» with controlled failures for documents.
        """

        actor = User.objects.filter(is_superuser=True).first() or User.objects.filter(is_active=True).first()
        branch = Branch.objects.filter(is_active=True).first()
        customer = Customer.objects.filter(is_deleted=False).first()
        vehicle = Vehicle.objects.filter(is_deleted=False).select_related("brand", "model").first()
        sale = SaleRecord.objects.filter(is_deleted=False).first()

        categories = [
            ("Contratos", DocumentCategory.Scope.SALE),
            ("Expediente de cliente", DocumentCategory.Scope.CUSTOMER),
            ("Documentos vehiculares", DocumentCategory.Scope.VEHICLE),
            ("Manuales y garantías", DocumentCategory.Scope.VEHICLE),
        ]
        category_map = {}
        for name, scope in categories:
            category, _ = DocumentCategory.objects.update_or_create(name=name, defaults={"scope": scope, "is_active": True})
            category_map[name] = category

        private_file = ContentFile(b"%PDF-1.4\n% Vinova Pro demo document\n", name="contrato_demo_multimarca.pdf")
        metadata = _uploaded_file_metadata(private_file)
        doc, created_doc = PrivateDocument.objects.update_or_create(
            title="Contrato demo multimarca",
            defaults={
                "document_type": PrivateDocument.DocumentType.CONTRACT,
                "category": category_map["Contratos"],
                "file": private_file,
                "status": PrivateDocument.Status.ACTIVE,
                "branch": branch,
                "customer": customer,
                "vehicle": vehicle,
                "sale": sale,
                "notes": "Documento demo privado. En producción no se expone por /static/, solo por descarga protegida.",
                "is_confidential": True,
                "uploaded_by": actor,
                **metadata,
            },
        )

        image_bytes = (
            b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc``\x00\x00\x00\x04\x00\x01"
            b"\xf6\x178U\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        asset_file = ContentFile(image_bytes, name="vehiculo_demo_multimarca.png")
        asset_metadata = _uploaded_file_metadata(asset_file)
        asset, created_asset = ReusableAsset.objects.update_or_create(
            title="Imagen demo multimarca",
            defaults={
                "asset_type": ReusableAsset.AssetType.VEHICLE_IMAGE,
                "file": asset_file,
                "visibility": ReusableAsset.Visibility.PUBLIC,
                "description": "Recurso demo público para validar galería y librería de medios.",
                "alt_text": "Vehículo demo multimarca",
                "branch": branch,
                "uploaded_by": actor,
                "is_active": True,
                **asset_metadata,
            },
        )

        media_created = False
        if vehicle and not vehicle.media.exists():
            vehicle_file = ContentFile(image_bytes, name="galeria_vehiculo_demo.png")
            vehicle_metadata = _uploaded_file_metadata(vehicle_file)
            resource = VehicleResource.objects.create(
                title="Foto principal demo",
                resource_type=VehicleResource.ResourceType.IMAGE,
                file=vehicle_file,
                file_hash=vehicle_metadata["file_hash"],
                mime_type=vehicle_metadata["mime_type"],
                uploaded_by=actor,
            )
            VehicleMedia.objects.create(vehicle=vehicle, resource=resource, media_type=VehicleMedia.MediaType.HERO, title="Foto principal", alt_text=str(vehicle), order=0, is_public=True)
            media_created = True

        self.stdout.write(
            self.style.SUCCESS(
                f"Documentos demo listos. Documento creado/actualizado: {doc.pk}. Recurso: {asset.pk}. Multimedia vehículo creada: {media_created}."
            )
        )
