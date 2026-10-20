"""ES: Este módulo especifica regresiones ejecutables para el dominio de privacidad.

EN: This module specifies executable regressions for the privacy domain.

Contexto existente / Existing context:
Regression coverage for privacy in the privacy domain.
"""

import json

import pytest
from django.conf import settings
from django.test import override_settings

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.customers.models import Customer, CustomerNote
from apps.leads.models import Lead
from apps.privacy.models import ConsentRecord, DataSubjectRequest
from apps.privacy.services import anonymize_customer, create_subject_export


pytestmark = pytest.mark.django_db


def make_user(django_user_model, *permissions):
    user = django_user_model.objects.create_user(username="privacy-admin", email="privacy@example.com", password="test12345")
    role = Role.objects.create(code="privacy-test", name="Privacy test", level=2)
    perms = [PermissionCode.objects.create(module=code.split('.')[0], code=code, name=code) for code in permissions]
    role.permissions.set(perms)
    UserRole.objects.create(user=user, role=role)
    return user


def test_public_data_subject_request(client):
    response = client.post(
        "/privacy/request/",
        {
            "request_type": DataSubjectRequest.RequestType.ACCESS,
            "requester_name": "Ana Pérez",
            "requester_email": "ana@example.com",
            "requester_phone": "",
            "identification_hint": "1234",
            "description": "Deseo conocer mis datos.",
            "privacy_acknowledgement": "on",
            "website": "",
        },
    )
    assert response.status_code == 302
    item = DataSubjectRequest.objects.get()
    assert item.status == DataSubjectRequest.Status.IDENTITY_PENDING
    assert item.metadata["ip_hash"]


def test_lead_consent_is_captured():
    lead = Lead.objects.create(
        full_name="Carlos Cliente",
        email="carlos@example.com",
        consent_data_processing=True,
        source=Lead.Source.WEB_CATALOG,
    )
    consent = ConsentRecord.objects.get(lead=lead)
    assert consent.status == ConsentRecord.Status.GRANTED
    assert consent.subject_email == "carlos@example.com"
    assert consent.notice_version == settings.VINOVA_PRIVACY_NOTICE_VERSION
    assert consent.evidence["notice_version"] == settings.VINOVA_PRIVACY_NOTICE_VERSION


def test_customer_export_is_private_and_hashed(tmp_path, django_user_model):
    actor = make_user(django_user_model, "privacy.view", "privacy.export")
    customer = Customer.objects.create(first_name="María", last_name="López", email="maria@example.com", phone="0999999999")
    request_obj = DataSubjectRequest.objects.create(
        request_type=DataSubjectRequest.RequestType.EXPORT,
        status=DataSubjectRequest.Status.VERIFIED,
        customer=customer,
        requester_name="María López",
        requester_email="maria@example.com",
        description="Exportar mis datos",
    )
    private = tmp_path / "private"
    private.mkdir()
    with override_settings(PRIVATE_STORAGE_ROOT=private):
        job = create_subject_export(actor=actor, request_obj=request_obj)
        assert job.sha256
        path = private / job.file_path
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["customer"]["email"] == "maria@example.com"
        assert job.status == job.Status.COMPLETED


def test_anonymization_requires_approved_request_and_clears_personal_data(django_user_model):
    actor = make_user(django_user_model, "privacy.view", "privacy.anonymize")
    customer = Customer.objects.create(
        first_name="Pedro", last_name="Gómez", identification_number="0102030405", email="pedro@example.com",
        phone="0991111111", whatsapp="0991111111", address="Dirección", city="Quito", province="Pichincha",
    )
    CustomerNote.objects.create(customer=customer, title="Llamar", body="Contenido sensible")
    Lead.objects.create(full_name="Pedro Gómez", email="pedro@example.com", customer=customer)
    request_obj = DataSubjectRequest.objects.create(
        request_type=DataSubjectRequest.RequestType.ANONYMIZATION,
        status=DataSubjectRequest.Status.APPROVED,
        customer=customer,
        requester_name="Pedro Gómez",
        requester_email="pedro@example.com",
        description="Anonimizar",
    )
    record = anonymize_customer(actor=actor, request_obj=request_obj)
    customer.refresh_from_db()
    request_obj.refresh_from_db()
    assert customer.identification_number is None
    assert customer.email == ""
    assert customer.first_name == "Cliente"
    assert customer.notes.get().body == "Contenido eliminado por anonimización."
    assert customer.crm_leads.get().email == ""
    assert request_obj.status == DataSubjectRequest.Status.COMPLETED
    assert record.before_hash


def test_privacy_dashboard_requires_permission(client, django_user_model):
    user = django_user_model.objects.create_user(username="plain-privacy", email="plain-privacy@example.com", password="test12345")
    client.force_login(user)
    assert client.get("/dashboard/privacy/").status_code == 403


def test_completed_revocation_request_revokes_active_consents(django_user_model):
    from apps.privacy.services import update_request_status

    actor = make_user(django_user_model, "privacy.view", "privacy.manage")
    customer = Customer.objects.create(first_name="Lucía", last_name="Mora", email="lucia@example.com")
    ConsentRecord.objects.create(
        customer=customer,
        purpose=ConsentRecord.Purpose.MARKETING,
        status=ConsentRecord.Status.GRANTED,
        subject_name="Lucía Mora",
        subject_email="lucia@example.com",
    )
    request_obj = DataSubjectRequest.objects.create(
        request_type=DataSubjectRequest.RequestType.CONSENT_REVOCATION,
        status=DataSubjectRequest.Status.VERIFIED,
        customer=customer,
        requester_name="Lucía Mora",
        requester_email="lucia@example.com",
        description="Revocar consentimiento",
    )
    update_request_status(
        actor=actor,
        request_obj=request_obj,
        status=DataSubjectRequest.Status.COMPLETED,
        resolution="Consentimiento revocado.",
    )
    consent = ConsentRecord.objects.get(customer=customer)
    assert consent.status == ConsentRecord.Status.REVOKED
    assert consent.revoked_at is not None
