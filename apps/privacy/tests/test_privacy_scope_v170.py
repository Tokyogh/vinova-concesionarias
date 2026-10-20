"""ES: Este módulo especifica regresiones ejecutables para el dominio de privacidad.

EN: This module specifies executable regressions for the privacy domain.

Contexto existente / Existing context:
Regression coverage for privacy scope v170 in the privacy domain.
"""

from __future__ import annotations

import pytest
from django.urls import reverse

from apps.accounts.models import PermissionCode, Role, UserRole
from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer
from apps.privacy.models import ConsentRecord, DataExportJob, DataSubjectRequest, RetentionPolicy


pytestmark = pytest.mark.django_db


@pytest.fixture
def scoped_privacy_context(django_user_model):
    company = Company.objects.create(
        legal_name="Privacy Scope SA",
        commercial_name="Privacy Scope",
        ruc="1799999999008",
    )
    branch_a = Branch.objects.create(company=company, name="Norte", code="PRIV-A", city="Quito")
    branch_b = Branch.objects.create(company=company, name="Sur", code="PRIV-B", city="Quito")
    permissions = [
        PermissionCode.objects.create(module="privacy", code=code, name=code)
        for code in (
            "privacy.view",
            "privacy.manage",
            "privacy.export",
            "privacy.anonymize",
        )
    ]
    manager_role = Role.objects.create(code="privacy-scope-manager", name="Privacy scope manager")
    manager_role.permissions.set(permissions)
    employee_role = Role.objects.create(code="privacy-scope-employee", name="Privacy scope employee")
    manager = django_user_model.objects.create_user(
        username="privacy-scope-manager",
        email="privacy-scope-manager@example.com",
        password="test12345",
    )
    employee_a = django_user_model.objects.create_user(
        username="privacy-scope-a",
        email="privacy-scope-a@example.com",
        password="test12345",
    )
    employee_b = django_user_model.objects.create_user(
        username="privacy-scope-b",
        email="privacy-scope-b@example.com",
        password="test12345",
    )
    UserRole.objects.create(user=manager, role=manager_role, branch=branch_a)
    UserRole.objects.create(user=employee_a, role=employee_role, branch=branch_a)
    UserRole.objects.create(user=employee_b, role=employee_role, branch=branch_b)
    customer_a = Customer.objects.create(first_name="Ana", email="privacy-a@example.com", assigned_branch=branch_a)
    customer_b = Customer.objects.create(first_name="Bea", email="privacy-b@example.com", assigned_branch=branch_b)
    request_a = DataSubjectRequest.objects.create(
        request_type=DataSubjectRequest.RequestType.ACCESS,
        customer=customer_a,
        requester_name="Ana",
        requester_email=customer_a.email,
        description="Acceso",
    )
    request_b = DataSubjectRequest.objects.create(
        request_type=DataSubjectRequest.RequestType.ACCESS,
        customer=customer_b,
        requester_name="Bea",
        requester_email=customer_b.email,
        description="Acceso",
    )
    ConsentRecord.objects.create(customer=customer_a, subject_name="Ana", subject_email=customer_a.email)
    ConsentRecord.objects.create(customer=customer_b, subject_name="Bea", subject_email=customer_b.email)
    DataExportJob.objects.create(request=request_a, customer=customer_a)
    DataExportJob.objects.create(request=request_b, customer=customer_b)
    RetentionPolicy.objects.create(code="privacy-scope", name="Privacy scope", data_category="customers")
    return manager, employee_a, employee_b, customer_a, customer_b, request_a, request_b


def test_privacy_api_and_html_are_branch_scoped(client, scoped_privacy_context):
    manager, _, _, customer_a, customer_b, request_a, request_b = scoped_privacy_context
    client.force_login(manager)

    response = client.get("/api/data-subject-requests/")
    assert response.status_code == 200
    request_ids = {item["public_id"] for item in response.json()["results"]}
    assert str(request_a.public_id) in request_ids
    assert str(request_b.public_id) not in request_ids

    consent_response = client.get("/api/privacy-consents/")
    assert consent_response.status_code == 200
    consent_customer_ids = {item["customer"] for item in consent_response.json()["results"]}
    assert customer_a.pk in consent_customer_ids
    assert customer_b.pk not in consent_customer_ids

    export_response = client.get("/api/data-exports/")
    assert export_response.status_code == 200
    export_customer_ids = {item["customer"] for item in export_response.json()["results"]}
    assert customer_a.pk in export_customer_ids
    assert customer_b.pk not in export_customer_ids

    response = client.get(reverse("privacy:request_list"))
    assert response.status_code == 200
    assert request_a in response.context["requests_list"]
    assert request_b not in response.context["requests_list"]
    assert client.get(reverse("privacy:request_detail", kwargs={"public_id": request_b.public_id})).status_code == 404
    dashboard = client.get(reverse("privacy:dashboard"))
    assert dashboard.context["metrics"]["requests_total"] == 1


def test_privacy_mutations_and_form_relations_reject_other_branch(client, scoped_privacy_context):
    manager, employee_a, employee_b, customer_a, customer_b, _, request_b = scoped_privacy_context
    client.force_login(manager)

    response = client.get(reverse("privacy:request_create"))
    assert response.status_code == 200
    assert customer_a in response.context["form"].fields["customer"].queryset
    assert customer_b not in response.context["form"].fields["customer"].queryset
    assert employee_a in response.context["form"].fields["assigned_to"].queryset
    assert employee_b not in response.context["form"].fields["assigned_to"].queryset

    assert client.post(reverse("privacy:request_status", kwargs={"public_id": request_b.public_id}), {}).status_code == 404
    assert client.post(reverse("privacy:request_export", kwargs={"public_id": request_b.public_id})).status_code == 404
    assert client.post(reverse("privacy:request_anonymize", kwargs={"public_id": request_b.public_id})).status_code == 404


def test_retention_policy_requires_global_privacy_permission(client, scoped_privacy_context):
    manager, *_ = scoped_privacy_context
    client.force_login(manager)

    assert client.get(reverse("privacy:retention_list")).status_code == 403
    assert client.get("/api/retention-policies/").status_code == 403
