"""ES: Este módulo especifica regresiones ejecutables para el dominio de portal cliente.

EN: This module specifies executable regressions for the portal domain.

Contexto existente / Existing context:
Regression coverage for documents in the portal domain.
"""

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.audit.models import AuditLog
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer
from apps.documents.forms import ReusableAssetForm
from apps.documents.models import PrivateDocument, ReusableAsset
from apps.portal.selectors import portal_manuals_queryset, portal_private_documents_queryset
from apps.vehicles.models import CustomerVehicle, Vehicle, VehicleBrand, VehicleModel


@pytest.fixture
def document_portal_context(db, django_user_model):
    permission, _ = PermissionCode.objects.update_or_create(
        code="portal.access", defaults={"module": "portal", "name": "Acceso al portal"}
    )
    role, _ = Role.objects.update_or_create(
        code="cliente", defaults={"name": "Cliente", "level": 100, "is_active": True}
    )
    role.permissions.add(permission)
    company = Company.objects.create(
        legal_name="Documentos Portal S.A.", commercial_name="Documentos Portal", ruc="1790000000069"
    )
    branch = Branch.objects.create(company=company, name="Matriz documental", code="DOC-POR")
    user = django_user_model.objects.create_user(
        username="document-client", email="document-client@example.com", password="x"
    )
    UserRole.objects.create(user=user, role=role)
    customer = Customer.objects.create(
        first_name="Cliente",
        last_name="Documentos",
        email=user.email,
        account=user,
        assigned_branch=branch,
        status=Customer.Status.ACTIVE,
    )
    brand = VehicleBrand.objects.create(name="Document Brand")
    model = VehicleModel.objects.create(brand=brand, name="Document Model")
    vehicle = Vehicle.objects.create(
        brand=brand, model=model, branch=branch, year=2026, public_slug="document-portal"
    )
    link = CustomerVehicle.objects.create(customer=customer, vehicle=vehicle)
    return user, customer, role, branch, model, vehicle, link


def _pdf(name="archivo.pdf"):
    return SimpleUploadedFile(name, b"%PDF-1.4 portal document", content_type="application/pdf")


@pytest.mark.django_db
def test_manual_form_requires_vehicle_model():
    form = ReusableAssetForm(
        data={
            "title": "Manual sin modelo",
            "asset_type": ReusableAsset.AssetType.MANUAL,
            "visibility": ReusableAsset.Visibility.PUBLIC,
            "is_active": True,
        },
        files={"file": _pdf("manual.pdf")},
    )
    assert not form.is_valid()
    assert "vehicle_model" in form.errors


@pytest.mark.django_db
def test_portal_lists_only_own_documents_and_matching_published_manuals(client, document_portal_context):
    user, customer, _, branch, model, vehicle, _ = document_portal_context
    own = PrivateDocument.objects.create(
        title="Contrato personal",
        document_type=PrivateDocument.DocumentType.CONTRACT,
        customer=customer,
        branch=branch,
        file=_pdf("contrato.pdf"),
        status=PrivateDocument.Status.ACTIVE,
    )
    generic_vehicle = PrivateDocument.objects.create(
        title="Garantía de unidad",
        document_type=PrivateDocument.DocumentType.WARRANTY,
        vehicle=vehicle,
        branch=branch,
        file=_pdf("garantia.pdf"),
        status=PrivateDocument.Status.ACTIVE,
    )
    foreign_customer = Customer.objects.create(first_name="Otro", email="otro-doc@example.com")
    hidden = PrivateDocument.objects.create(
        title="Documento ajeno",
        document_type=PrivateDocument.DocumentType.LEGAL,
        customer=foreign_customer,
        vehicle=vehicle,
        branch=branch,
        file=_pdf("ajeno.pdf"),
        status=PrivateDocument.Status.ACTIVE,
    )
    matching_manual = ReusableAsset.objects.create(
        title="Manual correcto",
        asset_type=ReusableAsset.AssetType.MANUAL,
        visibility=ReusableAsset.Visibility.PUBLIC,
        vehicle_model=model,
        vehicle_year=2026,
        file=_pdf("manual-correcto.pdf"),
    )
    ReusableAsset.objects.create(
        title="Manual año incorrecto",
        asset_type=ReusableAsset.AssetType.MANUAL,
        visibility=ReusableAsset.Visibility.PUBLIC,
        vehicle_model=model,
        vehicle_year=2025,
        file=_pdf("manual-incorrecto.pdf"),
    )
    ReusableAsset.objects.create(
        title="Manual interno",
        asset_type=ReusableAsset.AssetType.MANUAL,
        visibility=ReusableAsset.Visibility.INTERNAL,
        vehicle_model=model,
        vehicle_year=2026,
        file=_pdf("manual-interno.pdf"),
    )

    assert set(portal_private_documents_queryset(customer).values_list("pk", flat=True)) == {
        own.pk,
        generic_vehicle.pk,
    }
    assert list(portal_manuals_queryset(customer).values_list("pk", flat=True)) == [matching_manual.pk]

    client.force_login(user)
    response = client.get(reverse("portal:document_list"))
    content = response.content.decode()
    assert response.status_code == 200
    assert "Contrato personal" in content
    assert "Garantía de unidad" in content
    assert "Manual correcto" in content
    assert "Documento ajeno" not in content
    assert "Manual año incorrecto" not in content
    assert client.get(reverse("portal:document_detail", kwargs={"pk": hidden.pk})).status_code == 404
    filtered = client.get(
        reverse("portal:document_list"),
        {"q": "Contrato", "document_type": PrivateDocument.DocumentType.CONTRACT},
    ).content.decode()
    assert "Contrato personal" in filtered
    assert "Garantía de unidad" not in filtered


@pytest.mark.django_db
def test_transfer_does_not_move_customer_documents_and_revokes_generic_vehicle_access(
    client, document_portal_context, django_user_model
):
    user, customer, role, branch, _, vehicle, link = document_portal_context
    personal = PrivateDocument.objects.create(
        title="Documento del propietario anterior",
        document_type=PrivateDocument.DocumentType.CONTRACT,
        customer=customer,
        vehicle=vehicle,
        branch=branch,
        file=_pdf("anterior.pdf"),
    )
    generic = PrivateDocument.objects.create(
        title="Documento transferible de la unidad",
        document_type=PrivateDocument.DocumentType.VEHICLE_DOC,
        vehicle=vehicle,
        branch=branch,
        file=_pdf("unidad.pdf"),
    )
    link.is_active = False
    link.save(update_fields=["is_active"])
    new_user = django_user_model.objects.create_user(
        username="new-document-client", email="new-document-client@example.com", password="x"
    )
    UserRole.objects.create(user=new_user, role=role)
    new_customer = Customer.objects.create(
        first_name="Nuevo",
        email=new_user.email,
        account=new_user,
        status=Customer.Status.ACTIVE,
    )
    CustomerVehicle.objects.create(customer=new_customer, vehicle=vehicle)

    assert set(portal_private_documents_queryset(customer).values_list("pk", flat=True)) == {personal.pk}
    assert set(portal_private_documents_queryset(new_customer).values_list("pk", flat=True)) == {generic.pk}
    client.force_login(new_user)
    assert client.get(reverse("portal:document_detail", kwargs={"pk": personal.pk})).status_code == 404


@pytest.mark.django_db
def test_portal_downloads_are_protected_and_audited(client, document_portal_context):
    user, customer, _, branch, model, vehicle, _ = document_portal_context
    document = PrivateDocument.objects.create(
        title="Documento protegido",
        document_type=PrivateDocument.DocumentType.VEHICLE_DOC,
        vehicle=vehicle,
        branch=branch,
        file=_pdf("protegido.pdf"),
        original_name="protegido.pdf",
        mime_type="application/pdf",
    )
    manual = ReusableAsset.objects.create(
        title="Manual descargable",
        asset_type=ReusableAsset.AssetType.MANUAL,
        visibility=ReusableAsset.Visibility.PUBLIC,
        vehicle_model=model,
        vehicle_year=2026,
        file=_pdf("manual-descargable.pdf"),
        original_name="manual-descargable.pdf",
        mime_type="application/pdf",
    )
    assert client.get(reverse("portal:document_download", kwargs={"pk": document.pk})).status_code == 302
    client.force_login(user)

    document_response = client.get(reverse("portal:document_download", kwargs={"pk": document.pk}))
    manual_response = client.get(reverse("portal:manual_download", kwargs={"pk": manual.pk}))

    assert document_response.status_code == 200
    assert document_response["Cache-Control"] == "private, no-store"
    assert document_response["X-Content-Type-Options"] == "nosniff"
    assert document_response["Content-Disposition"].startswith("attachment")
    assert manual_response.status_code == 200
    assert AuditLog.objects.filter(
        user=user, customer=customer, action="documents.private.download", object_id=str(document.pk)
    ).exists()
    assert AuditLog.objects.filter(
        user=user, customer=customer, action="documents.asset.download", object_id=str(manual.pk)
    ).exists()


@pytest.mark.django_db
def test_missing_portal_files_return_404_without_false_download_audit(client, document_portal_context):
    user, customer, _, branch, model, vehicle, _ = document_portal_context
    document = PrivateDocument.objects.create(
        title="Documento sin objeto",
        document_type=PrivateDocument.DocumentType.VEHICLE_DOC,
        vehicle=vehicle,
        branch=branch,
        file=_pdf("objeto-ausente.pdf"),
    )
    manual = ReusableAsset.objects.create(
        title="Manual sin objeto",
        asset_type=ReusableAsset.AssetType.MANUAL,
        visibility=ReusableAsset.Visibility.PUBLIC,
        vehicle_model=model,
        vehicle_year=2026,
        file=_pdf("manual-ausente.pdf"),
    )
    document.file.storage.delete(document.file.name)
    manual.file.storage.delete(manual.file.name)
    client.force_login(user)

    assert client.get(reverse("portal:document_download", kwargs={"pk": document.pk})).status_code == 404
    assert client.get(reverse("portal:manual_download", kwargs={"pk": manual.pk})).status_code == 404
    assert not AuditLog.objects.filter(
        user=user,
        customer=customer,
        action__in=("documents.private.download", "documents.asset.download"),
    ).exists()
