"""ES: Este módulo implementa consultas de lectura conscientes de autorización para el dominio de portal cliente.

EN: This module implements authorization-aware read queries for the portal domain.

Contexto existente / Existing context:
Read queries and authorization-aware selectors for the portal domain.
"""

from __future__ import annotations

from django.db.models import CharField, Count, F, IntegerField, OuterRef, Prefetch, Q, Subquery, Value
from django.db.models.functions import Coalesce
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.db.models.functions import TruncMonth

from apps.common.search import clean_search_query
from apps.common.modules import is_module_enabled
from apps.customers.models import Customer
from apps.documents.models import PrivateDocument, ReusableAsset
from apps.invoices.models import InvoiceRecord
from apps.notifications.models import NotificationMessage, NotificationRecipient
from apps.post_sales.models import ServiceOrder
from apps.vehicles.models import CustomerVehicle, VehicleMedia, VehiclePartSpecification


class PortalCustomerUnavailable(Exception):
    """The authenticated account has no Customer eligible for private portal access."""


def portal_customer_for_user(user) -> Customer:
    """Raíz única de ownership para todas las consultas privadas del portal."""
    customer_unread = (
        NotificationRecipient.objects.filter(
            customer_id=OuterRef("pk"),
            recipient_type=NotificationRecipient.RecipientType.CUSTOMER,
            status=NotificationRecipient.DeliveryStatus.UNREAD,
            notification__is_deleted=False,
            notification__status=NotificationMessage.Status.SENT,
        )
        .order_by()
        .values("customer_id")
        .annotate(total=Count("pk"))
        .values("total")
    )
    user_unread = (
        NotificationRecipient.objects.filter(
            user_id=OuterRef("account_id"),
            recipient_type=NotificationRecipient.RecipientType.USER,
            status=NotificationRecipient.DeliveryStatus.UNREAD,
            notification__is_deleted=False,
            notification__status=NotificationMessage.Status.SENT,
        )
        .order_by()
        .values("user_id")
        .annotate(total=Count("pk"))
        .values("total")
    )
    customer = (
        Customer.objects.filter(
            account=user,
            is_deleted=False,
            status__in=(Customer.Status.ACTIVE, Customer.Status.VIP),
        )
        .annotate(
            portal_customer_unread_count=Coalesce(
                Subquery(customer_unread, output_field=IntegerField()),
                Value(0),
            ),
            portal_user_unread_count=Coalesce(
                Subquery(user_unread, output_field=IntegerField()),
                Value(0),
            ),
        )
        .select_related("account", "assigned_branch", "assigned_branch__company")
        .first()
    )
    if customer is None:
        raise PortalCustomerUnavailable
    customer.portal_unread_count = customer.portal_customer_unread_count + customer.portal_user_unread_count
    return customer


def portal_dashboard_data(customer: Customer) -> dict:
    public_media = VehicleMedia.objects.filter(is_public=True).select_related("resource").order_by("order", "id")
    active_links = (
        CustomerVehicle.objects.filter(customer=customer, is_active=True)
        .select_related("vehicle", "vehicle__brand", "vehicle__model", "vehicle__branch")
        .prefetch_related(Prefetch("vehicle__media", queryset=public_media))
        .order_by("-created_at", "-id")
    )
    data = {
        "vehicle_count": active_links.count(),
        "recent_vehicles": list(active_links[:3]),
        "document_count": portal_private_documents_queryset(customer).count(),
        "manual_count": portal_manuals_queryset(customer).count(),
        "invoice_count": portal_invoices_queryset(customer).count(),
        "unread_notification_count": customer.portal_unread_count,
        "recent_activity": portal_recent_activity(customer),
    }
    if is_module_enabled("post_sales"):
        service_orders = portal_service_orders_queryset(customer)
        data["open_service_count"] = service_orders.filter(
            status__in=(ServiceOrder.Status.SCHEDULED, ServiceOrder.Status.IN_PROGRESS)
        ).count()
        data["next_service_order"] = (
            service_orders.filter(status=ServiceOrder.Status.SCHEDULED, scheduled_at__isnull=False)
            .order_by("scheduled_at")
            .first()
        )
        data["last_service_order"] = (
            service_orders.filter(
                status=ServiceOrder.Status.COMPLETED,
            )
            .order_by("-completed_at", "-updated_at")
            .first()
        )
        data["recent_service_orders"] = list(service_orders.filter(status=ServiceOrder.Status.COMPLETED)[:4])
        data["upcoming_service_orders"] = list(
            service_orders.filter(
                status__in=(ServiceOrder.Status.SCHEDULED, ServiceOrder.Status.IN_PROGRESS),
            ).order_by("scheduled_at", "created_at")[:4]
        )
        data["service_chart"] = _portal_service_chart(service_orders)
    return data


def _portal_service_chart(service_orders) -> list[dict]:
    """Return the same six-month completed-service series shown by LITE."""
    today = timezone.localdate()
    months: list[tuple[int, int]] = []
    year, month = today.year, today.month
    for offset in range(5, -1, -1):
        absolute_month = year * 12 + month - 1 - offset
        months.append((absolute_month // 12, absolute_month % 12 + 1))

    first_year, first_month = months[0]
    counts = {
        (row["month"].year, row["month"].month): row["total"]
        for row in service_orders.filter(
            status=ServiceOrder.Status.COMPLETED,
            completed_at__date__gte=timezone.datetime(first_year, first_month, 1).date(),
        )
        .annotate(month=TruncMonth("completed_at"))
        .values("month")
        .annotate(total=Count("pk"))
        .order_by("month")
        if row["month"] is not None
    }
    labels = ("Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic")
    maximum = max([*counts.values(), 1])
    return [
        {
            "label": labels[item_month - 1],
            "value": counts.get((item_year, item_month), 0),
            "height": round((counts.get((item_year, item_month), 0) / maximum) * 100),
        }
        for item_year, item_month in months
    ]


def portal_vehicle_links_queryset(customer: Customer, *, query: str = ""):
    public_media = VehicleMedia.objects.filter(is_public=True).select_related("resource").order_by("order", "id")
    queryset = (
        CustomerVehicle.objects.filter(customer=customer, is_active=True, vehicle__is_deleted=False)
        .select_related(
            "vehicle",
            "vehicle__brand",
            "vehicle__model",
            "vehicle__branch",
            "vehicle__branch__company",
        )
        .prefetch_related(Prefetch("vehicle__media", queryset=public_media))
        .order_by("-created_at", "-id")
    )
    text = clean_search_query(query)
    if text:
        queryset = queryset.filter(
            Q(vehicle__brand__name__icontains=text)
            | Q(vehicle__model__name__icontains=text)
            | Q(vehicle__version__icontains=text)
            | Q(vehicle__plate__istartswith=text)
        )
    return queryset


def portal_vehicle_link_detail(*, customer: Customer, link_pk: int) -> CustomerVehicle:
    public_media = VehicleMedia.objects.filter(is_public=True).select_related("resource").order_by("order", "id")
    specifications = VehiclePartSpecification.objects.select_related("image").order_by("order", "id")
    return get_object_or_404(
        CustomerVehicle.objects.filter(customer=customer, is_active=True, vehicle__is_deleted=False)
        .select_related(
            "vehicle",
            "vehicle__brand",
            "vehicle__model",
            "vehicle__branch",
            "vehicle__branch__company",
        )
        .prefetch_related(
            Prefetch("vehicle__media", queryset=public_media),
            Prefetch("vehicle__part_specs", queryset=specifications),
        ),
        pk=link_pk,
    )


def portal_service_orders_queryset(customer: Customer, *, query="", status=""):
    queryset = (
        ServiceOrder.objects.filter(
            customer=customer,
            vehicle__customer_links__customer=customer,
            vehicle__customer_links__is_active=True,
            vehicle__is_deleted=False,
        )
        .exclude(status=ServiceOrder.Status.DRAFT)
        .select_related("branch", "vehicle", "vehicle__brand", "vehicle__model", "responsible")
        .prefetch_related("lines")
        .distinct()
    )
    text = clean_search_query(query)
    if text:
        queryset = queryset.filter(
            Q(number__icontains=text)
            | Q(description__icontains=text)
            | Q(vehicle__brand__name__icontains=text)
            | Q(vehicle__model__name__icontains=text)
        )
    if status:
        queryset = queryset.filter(status=status)
    return queryset


def portal_service_order_detail(*, customer: Customer, order_pk: int) -> ServiceOrder:
    return get_object_or_404(
        portal_service_orders_queryset(customer).prefetch_related("history"),
        pk=order_pk,
    )


def portal_private_documents_queryset(customer: Customer, *, query="", document_type=""):
    """Documents explicitly assigned to the customer or generic to a currently owned vehicle.

    A document assigned to a previous customer never follows the vehicle to its new
    owner. Customer-specific documents remain in that customer's personal record.
    """
    queryset = (
        PrivateDocument.objects.filter(is_deleted=False, status=PrivateDocument.Status.ACTIVE)
        .filter(
            Q(customer=customer)
            | Q(
                customer__isnull=True,
                vehicle__customer_links__customer=customer,
                vehicle__customer_links__is_active=True,
                vehicle__is_deleted=False,
            )
        )
        .select_related("category", "branch", "vehicle", "vehicle__brand", "vehicle__model", "sale")
        .distinct()
        .order_by("-created_at", "-id")
    )
    text = clean_search_query(query)
    if text:
        queryset = queryset.filter(
            Q(title__icontains=text)
            | Q(original_name__icontains=text)
            | Q(vehicle__brand__name__icontains=text)
            | Q(vehicle__model__name__icontains=text)
        )
    if document_type:
        queryset = queryset.filter(document_type=document_type)
    return queryset


def portal_private_document_detail(*, customer: Customer, document_pk: int) -> PrivateDocument:
    return get_object_or_404(portal_private_documents_queryset(customer), pk=document_pk)


def portal_manuals_queryset(customer: Customer):
    active_links = CustomerVehicle.objects.filter(
        customer=customer,
        is_active=True,
        vehicle__is_deleted=False,
    ).select_related("vehicle")
    model_scope = Q(pk__in=[])
    for link in active_links:
        vehicle = link.vehicle
        match = Q(vehicle_model_id=vehicle.model_id) & (Q(vehicle_year__isnull=True) | Q(vehicle_year=vehicle.year))
        if vehicle.branch_id:
            match &= Q(branch__isnull=True) | Q(branch_id=vehicle.branch_id)
        else:
            match &= Q(branch__isnull=True)
        model_scope |= match
    return (
        ReusableAsset.objects.filter(
            model_scope,
            is_deleted=False,
            is_active=True,
            asset_type=ReusableAsset.AssetType.MANUAL,
            visibility=ReusableAsset.Visibility.PUBLIC,
        )
        .select_related("vehicle_model", "vehicle_model__brand", "branch")
        .order_by("vehicle_model__brand__name", "vehicle_model__name", "vehicle_year", "title")
    )


def portal_manual_detail(*, customer: Customer, asset_pk: int) -> ReusableAsset:
    return get_object_or_404(portal_manuals_queryset(customer), pk=asset_pk)


def portal_invoices_queryset(customer: Customer, *, query="", status=""):
    queryset = (
        InvoiceRecord.objects.filter(customer=customer, is_deleted=False)
        .exclude(status=InvoiceRecord.Status.DRAFT)
        .select_related("company", "branch", "customer", "sale", "sale__vehicle", "linked_document")
        .prefetch_related("lines", "payment_applications")
        .order_by("-issue_date", "-created_at")
    )
    text = clean_search_query(query)
    if text:
        queryset = queryset.filter(Q(number__icontains=text) | Q(notes__icontains=text))
    if status:
        queryset = queryset.filter(status=status)
    return queryset


def portal_invoice_detail(*, customer: Customer, invoice_pk: int) -> InvoiceRecord:
    return get_object_or_404(portal_invoices_queryset(customer), pk=invoice_pk)


def portal_notifications_queryset(
    customer: Customer,
    *,
    include_archived=False,
    query="",
    message_type="",
    delivery_status="",
):
    owned = Q(
        recipient_type=NotificationRecipient.RecipientType.CUSTOMER,
        customer=customer,
    )
    if customer.account_id:
        owned |= Q(
            recipient_type=NotificationRecipient.RecipientType.USER,
            user_id=customer.account_id,
        )
    queryset = NotificationRecipient.objects.filter(
        owned,
        notification__is_deleted=False,
        notification__status=NotificationMessage.Status.SENT,
    ).select_related(
        "notification",
        "notification__sender",
        "notification__related_vehicle",
        "notification__related_sale",
        "notification__related_document",
    )
    if not include_archived:
        queryset = queryset.exclude(status=NotificationRecipient.DeliveryStatus.ARCHIVED)
    text = clean_search_query(query)
    if text:
        queryset = queryset.filter(Q(notification__title__icontains=text) | Q(notification__body__icontains=text))
    if message_type:
        queryset = queryset.filter(notification__message_type=message_type)
    if delivery_status:
        queryset = queryset.filter(status=delivery_status)
    return queryset.order_by("-notification__sent_at", "-created_at")


def portal_notification_recipient_detail(*, customer: Customer, recipient_pk: int) -> NotificationRecipient:
    return get_object_or_404(portal_notifications_queryset(customer, include_archived=True), pk=recipient_pk)


def portal_recent_activity(customer: Customer, *, limit=8):
    """Return a bounded cross-domain timeline in one database round trip."""
    fields = ("activity_kind", "activity_title", "activity_at", "activity_target_id")
    streams = [
        CustomerVehicle.objects.filter(customer=customer, is_active=True)
        .order_by()
        .annotate(
            activity_kind=Value("vehicle", output_field=CharField()),
            activity_title=F("vehicle__model__name"),
            activity_at=F("created_at"),
            activity_target_id=F("pk"),
        )
        .values(*fields),
        portal_private_documents_queryset(customer)
        .order_by()
        .annotate(
            activity_kind=Value("document", output_field=CharField()),
            activity_title=F("title"),
            activity_at=F("created_at"),
            activity_target_id=F("pk"),
        )
        .values(*fields),
        portal_invoices_queryset(customer)
        .order_by()
        .annotate(
            activity_kind=Value("invoice", output_field=CharField()),
            activity_title=F("number"),
            activity_at=Coalesce("issued_at", "created_at"),
            activity_target_id=F("pk"),
        )
        .values(*fields),
        portal_notifications_queryset(customer)
        .order_by()
        .annotate(
            activity_kind=Value("notification", output_field=CharField()),
            activity_title=F("notification__title"),
            activity_at=F("notification__sent_at"),
            activity_target_id=F("pk"),
        )
        .values(*fields),
    ]
    if is_module_enabled("post_sales"):
        streams.append(
            portal_service_orders_queryset(customer)
            .order_by()
            .annotate(
                activity_kind=Value("service", output_field=CharField()),
                activity_title=F("number"),
                activity_at=F("updated_at"),
                activity_target_id=F("pk"),
            )
            .values(*fields)
        )
    rows = streams[0].union(*streams[1:], all=True).order_by("-activity_at")[:limit]
    routes = {
        "vehicle": "portal:vehicle_detail",
        "document": "portal:document_detail",
        "invoice": "portal:invoice_detail",
        "notification": "portal:notification_detail",
        "service": "portal:service_detail",
    }
    labels = {
        "vehicle": "Vehículo vinculado",
        "document": "Documento publicado",
        "invoice": "Comprobante emitido",
        "notification": "Notificación",
        "service": "Servicio actualizado",
    }
    return [
        {
            **row,
            "label": labels[row["activity_kind"]],
            "url": reverse(routes[row["activity_kind"]], kwargs={"pk": row["activity_target_id"]}),
        }
        for row in rows
    ]
