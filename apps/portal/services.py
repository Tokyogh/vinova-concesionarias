"""ES: Este módulo implementa servicios de negocio y efectos transaccionales para el dominio de portal cliente.

EN: This module implements business services and transactional effects for the portal domain.

Contexto existente / Existing context:
Transactional business services for the portal domain.
"""

from django.db import transaction

from apps.audit.services import audit_log
from apps.customers.models import Customer


EDITABLE_PROFILE_FIELDS = ("phone", "whatsapp", "address", "city", "province", "preferred_contact_method")


@transaction.atomic
def update_portal_customer_profile(*, actor, customer: Customer, form) -> Customer:
    customer = Customer.objects.select_for_update().get(pk=customer.pk, account=actor, is_deleted=False)
    before = {field: getattr(customer, field) for field in EDITABLE_PROFILE_FIELDS}
    for field in EDITABLE_PROFILE_FIELDS:
        setattr(customer, field, form.cleaned_data[field])
    customer.save(update_fields=[*EDITABLE_PROFILE_FIELDS, "updated_at"])
    audit_log(
        user=actor,
        action="portal.profile.update",
        target=customer,
        customer=customer,
        before=before,
        after={field: getattr(customer, field) for field in EDITABLE_PROFILE_FIELDS},
    )
    return customer
