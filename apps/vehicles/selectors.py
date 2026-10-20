"""ES: Este módulo implementa consultas de lectura conscientes de autorización para el dominio de vehículos.

EN: This module implements authorization-aware read queries for the vehicles domain.

Contexto existente / Existing context:
Read queries and authorization-aware selectors for the vehicles domain.
"""

from __future__ import annotations

from django.db.models import Prefetch, Q

from apps.accounts.scopes import scope_queryset_to_user_branches
from apps.common.search import clean_search_query, normalize_vin, plate_startswith_q
from apps.vehicles.models import (
    CustomerVehicle,
    Vehicle,
    VehicleBrand,
    VehicleLinkCode,
    VehicleMedia,
    VehicleModel,
    VehiclePartSpecification,
)

VEHICLE_SCOPE_PERMISSIONS = ("vehicles.view", "vehicles.manage", "vehicles.publish")


def accessible_vehicle_queryset(user, *, permission_codes=VEHICLE_SCOPE_PERMISSIONS):
    return scope_queryset_to_user_branches(
        Vehicle.objects.filter(is_deleted=False),
        user=user,
        permission_codes=permission_codes,
        branch_lookup="branch",
    )


def vehicle_catalog_queryset():
    return (
        Vehicle.objects.select_related("brand", "model", "branch", "branch__company")
        .prefetch_related(
            Prefetch("media", queryset=VehicleMedia.objects.select_related("resource").filter(is_public=True).order_by("order", "id")),
            Prefetch("part_specs", queryset=VehiclePartSpecification.objects.select_related("image").order_by("order", "id")),
            "highlights",
        )
        .filter(is_deleted=False)
        .exclude(status=Vehicle.Status.ARCHIVED)
    )


def public_vehicle_queryset():
    return vehicle_catalog_queryset().filter(
        status=Vehicle.Status.AVAILABLE,
        published_at__isnull=False,
    )


def internal_vehicle_queryset(
    *,
    user,
    query: str = "",
    status: str = "",
    branch=None,
    sort: str = "",
    vin: str = "",
    plate: str = "",
    internal_code: str = "",
    brand=None,
    model=None,
):
    qs = (
        accessible_vehicle_queryset(user)
        .select_related("brand", "model", "branch", "branch__company")
        .prefetch_related("media", "highlights")
    )
    text = clean_search_query(query)
    if text:
        qs = qs.filter(
            Q(brand__name__icontains=text)
            | Q(model__name__icontains=text)
            | Q(version__icontains=text)
            | Q(internal_code__icontains=text)
            | Q(vin__icontains=text)
            | Q(plate__icontains=text)
            | Q(color__icontains=text)
            | Q(branch__name__icontains=text)
            | Q(branch__city__icontains=text)
        )
    vin_q = normalize_vin(vin)
    if vin_q:
        qs = qs.filter(vin__istartswith=vin_q)
    plate_q = plate_startswith_q(plate)
    if plate_q:
        qs = qs.filter(plate_q)
    code_q = clean_search_query(internal_code)
    if code_q:
        qs = qs.filter(internal_code__istartswith=code_q)
    if brand:
        qs = qs.filter(brand=brand)
    if model:
        qs = qs.filter(model=model)
    if status:
        qs = qs.filter(status=status)
    if branch:
        qs = qs.filter(branch=branch)
    ordering = {
        "newest": ("-created_at",), "price_asc": ("price", "-created_at"),
        "price_desc": ("-price", "-created_at"), "year_desc": ("-year", "-created_at"),
    }.get(sort, ("-is_featured", "-created_at"))
    return qs.order_by(*ordering)


def vehicle_detail_queryset(user, *, permission_codes=VEHICLE_SCOPE_PERMISSIONS):
    return (
        accessible_vehicle_queryset(user, permission_codes=permission_codes)
        .select_related("brand", "model", "branch", "branch__company")
        .prefetch_related(
            Prefetch("media", queryset=VehicleMedia.objects.select_related("resource").order_by("order", "id")),
            Prefetch("part_specs", queryset=VehiclePartSpecification.objects.select_related("image").order_by("order", "id")),
            "highlights",
        )
    )


def brand_list_queryset():
    return VehicleBrand.objects.order_by("name")


def vehicle_links_queryset(vehicle):
    return (
        CustomerVehicle.objects.filter(vehicle=vehicle)
        .select_related("customer", "linked_via")
        .order_by("-created_at", "-id")
    )


def vehicle_link_codes_queryset(vehicle):
    return (
        VehicleLinkCode.objects.filter(vehicle=vehicle)
        .select_related("created_by", "used_by", "revoked_by")
        .order_by("-created_at", "-id")
    )


def model_list_queryset():
    return VehicleModel.objects.select_related("brand").order_by("brand__name", "name")
