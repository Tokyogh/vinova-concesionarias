"""ES: Este módulo implementa consultas de lectura conscientes de autorización para el dominio de clientes.

EN: This module implements authorization-aware read queries for the customers domain.

Contexto existente / Existing context:
Read queries and authorization-aware selectors for the customers domain.
"""

from __future__ import annotations

from django.db.models import Count, Q

from apps.accounts.scopes import accessible_branches_queryset, accessible_users_queryset, scope_queryset_to_user_branches
from apps.common.search import clean_identification_query, clean_name_query, clean_phone_query, clean_search_query, normalize_vin, plate_startswith_q
from apps.common.validators import is_valid_ec_cedula, is_valid_ec_ruc
from apps.customers.models import Customer, CustomerNote, CustomerVehicleInterest
from apps.vehicles.models import CustomerVehicle, Vehicle


CUSTOMER_PERMISSION_CODES = ("customers.view", "customers.manage")


def accessible_customer_queryset(user, *, permission_codes=CUSTOMER_PERMISSION_CODES):
    return scope_queryset_to_user_branches(
        Customer.objects.filter(is_deleted=False),
        user=user,
        permission_codes=permission_codes,
        branch_lookup="assigned_branch",
    )


def accessible_customer_branches_queryset(user, *, permission_codes=CUSTOMER_PERMISSION_CODES):
    return accessible_branches_queryset(user, permission_codes=permission_codes)


def accessible_customer_advisors_queryset(user, *, permission_codes=CUSTOMER_PERMISSION_CODES):
    return accessible_users_queryset(user, permission_codes=permission_codes)


def accessible_customer_vehicles_queryset(user, *, permission_codes=CUSTOMER_PERMISSION_CODES):
    return (
        scope_queryset_to_user_branches(
            Vehicle.objects.filter(is_deleted=False),
            user=user,
            permission_codes=permission_codes,
        )
        .select_related("brand", "model", "model__brand")
        .order_by("brand__name", "model__name", "-year")
    )


def _identification_q(value: str) -> Q:
    """Filtra por cédula/RUC normalizada con prioridad a la coincidencia exacta.

    Cuando el texto es una cédula o RUC ecuatoriano válido se consulta por el
    identificador normalizado (consulta indexada). En caso contrario se usa una
    coincidencia parcial acotada al mínimo de dígitos para no enumerar la base.
    """
    digits = clean_identification_query(value)
    if not digits:
        return Q()
    if len(digits) >= 10 and (is_valid_ec_cedula(digits) or is_valid_ec_ruc(digits)):
        return Q(identification_number=digits)
    return Q(identification_number__icontains=digits)


def customer_list_queryset(
    *,
    user,
    query: str = "",
    status: str = "",
    customer_type: str = "",
    branch=None,
    sort: str = "",
    identification: str = "",
    first_name: str = "",
    last_name: str = "",
    email: str = "",
    phone: str = "",
    plate: str = "",
    vin: str = "",
):
    """Return the accessible customer list with normalized business filters."""

    qs = (
        accessible_customer_queryset(user)
        .select_related("assigned_branch", "assigned_branch__company", "assigned_advisor", "created_by")
    )
    text = clean_search_query(query)
    if text:
        qs = qs.filter(
            Q(first_name__icontains=text)
            | Q(last_name__icontains=text)
            | Q(business_name__icontains=text)
            | Q(identification_number__icontains=text)
            | Q(email__icontains=text)
            | Q(phone__icontains=text)
            | Q(whatsapp__icontains=text)
            | Q(city__icontains=text)
            | Q(province__icontains=text)
            | Q(assigned_branch__name__icontains=text)
        )
    identification_q = _identification_q(identification)
    if identification_q:
        qs = qs.filter(identification_q)
    first_name_q = clean_name_query(first_name)
    if first_name_q:
        qs = qs.filter(first_name__icontains=first_name_q)
    last_name_q = clean_name_query(last_name)
    if last_name_q:
        qs = qs.filter(last_name__icontains=last_name_q)
    email_q = clean_search_query(email)
    if email_q:
        qs = qs.filter(email__icontains=email_q)
    phone_q = clean_phone_query(phone)
    if phone_q:
        qs = qs.filter(
            Q(phone__icontains=phone_q) | Q(whatsapp__icontains=phone_q)
        )
    plate_q = plate_startswith_q(plate, field="vehicle_interests__vehicle__plate")
    if plate_q:
        qs = qs.filter(plate_q)
    vin_q = normalize_vin(vin)
    if vin_q:
        qs = qs.filter(vehicle_interests__vehicle__vin__istartswith=vin_q)
    if plate_q or vin_q:
        qs = qs.distinct()
    if status:
        qs = qs.filter(status=status)
    if customer_type:
        qs = qs.filter(customer_type=customer_type)
    if branch:
        qs = qs.filter(assigned_branch=branch)
    ordering = {
        "name_asc": ("business_name", "first_name", "last_name"),
        "name_desc": ("-business_name", "-first_name", "-last_name"),
        "oldest": ("created_at",),
    }.get(sort, ("-created_at",))
    return qs.order_by(*ordering)


def customer_detail_queryset(*, user, permission_codes=CUSTOMER_PERMISSION_CODES):
    return (
        accessible_customer_queryset(user, permission_codes=permission_codes)
        .select_related("assigned_branch", "assigned_branch__company", "assigned_advisor", "created_by")
        .prefetch_related("notes__created_by", "vehicle_interests__vehicle", "vehicle_interests__vehicle__brand", "vehicle_interests__vehicle__model")
    )


def linkable_customer_queryset(*, user):
    return accessible_customer_queryset(user).select_related("assigned_branch").order_by("first_name", "last_name", "business_name")


def customer_metrics(*, user):
    base = accessible_customer_queryset(user)
    return {
        "total": base.count(),
        "prospect": base.filter(status=Customer.Status.PROSPECT).count(),
        "active": base.filter(status__in=[Customer.Status.ACTIVE, Customer.Status.VIP]).count(),
        "archived": base.filter(status=Customer.Status.ARCHIVED).count(),
        "with_branch": base.filter(assigned_branch__isnull=False).count(),
    }


def customer_status_distribution(*, user):
    return base_distribution(accessible_customer_queryset(user), "status")


def base_distribution(queryset, field_name):
    return queryset.values(field_name).annotate(total=Count("id")).order_by(field_name)


def customer_notes_queryset(customer: Customer):
    return CustomerNote.objects.select_related("created_by").filter(customer=customer).order_by("-created_at")


def customer_interests_queryset(customer: Customer):
    return CustomerVehicleInterest.objects.select_related("vehicle", "vehicle__brand", "vehicle__model", "created_by").filter(customer=customer).order_by("-created_at")


def customer_garage_queryset(customer: Customer):
    return (
        CustomerVehicle.objects.filter(customer=customer)
        .select_related("vehicle__brand", "vehicle__model", "vehicle__branch", "linked_via")
        .order_by("-created_at", "-id")
    )
