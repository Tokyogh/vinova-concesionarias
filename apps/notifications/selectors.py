"""ES: Este módulo implementa consultas de lectura conscientes de autorización para el dominio de notificaciones.

EN: This module implements authorization-aware read queries for the notifications domain.

Contexto existente / Existing context:
Read queries and authorization-aware selectors for the notifications domain.
"""

from __future__ import annotations

from django.db.models import Count, Q

from apps.accounts.scopes import accessible_branch_ids, scope_queryset_to_user_branches
from apps.notifications.models import Campaign, NotificationMessage, NotificationRecipient, NotificationTemplate


def notification_messages_queryset(*, user, permission_code="notifications.send", include_personal=True, query="", message_type="", priority="", branch=None):
    qs = NotificationMessage.objects.filter(is_deleted=False).select_related(
        "sender", "branch", "related_customer", "related_vehicle", "related_sale", "related_document", "template"
    ).prefetch_related("recipients")
    branch_ids = accessible_branch_ids(user, permission_codes=(permission_code,))
    if branch_ids is not None:
        branch_filter = Q(branch_id__in=branch_ids)
        if include_personal:
            branch_filter |= Q(sender=user) | Q(recipients__user=user)
        qs = qs.filter(branch_filter).distinct()
    if query:
        qs = qs.filter(
            Q(title__icontains=query)
            | Q(body__icontains=query)
            | Q(sender__first_name__icontains=query)
            | Q(sender__last_name__icontains=query)
            | Q(sender__email__icontains=query)
            | Q(related_customer__first_name__icontains=query)
            | Q(related_customer__last_name__icontains=query)
            | Q(related_customer__business_name__icontains=query)
            | Q(related_customer__identification_number__icontains=query)
            | Q(related_vehicle__internal_code__icontains=query)
            | Q(related_vehicle__vin__icontains=query)
            | Q(related_vehicle__plate__icontains=query)
            | Q(related_sale__number__icontains=query)
        )
    if message_type:
        qs = qs.filter(message_type=message_type)
    if priority:
        qs = qs.filter(priority=priority)
    if branch:
        qs = qs.filter(branch=branch)
    return qs.annotate(total_recipients=Count("recipients", distinct=True)).order_by("-sent_at", "-created_at")


def notification_detail_queryset(*, user, permission_code="notifications.send", include_personal=True):
    qs = NotificationMessage.objects.filter(is_deleted=False).select_related(
        "sender", "branch", "related_customer", "related_vehicle", "related_sale", "related_document", "template"
    ).prefetch_related("recipients__user", "recipients__customer")
    branch_ids = accessible_branch_ids(user, permission_codes=(permission_code,))
    if branch_ids is None:
        return qs
    branch_filter = Q(branch_id__in=branch_ids)
    if include_personal:
        branch_filter |= Q(sender=user) | Q(recipients__user=user)
    return qs.filter(branch_filter).distinct()


def user_inbox_queryset(user, *, query="", status=""):
    qs = NotificationRecipient.objects.filter(
        user=user,
        notification__is_deleted=False,
        notification__status=NotificationMessage.Status.SENT,
    ).select_related("notification", "notification__sender", "notification__branch")
    if query:
        qs = qs.filter(Q(notification__title__icontains=query) | Q(notification__body__icontains=query) | Q(notification__sender__email__icontains=query))
    if status:
        qs = qs.filter(status=status)
    return qs.order_by("-notification__sent_at", "-created_at")


def sent_notifications_queryset(user=None, *, query=""):
    qs = notification_messages_queryset(user=user, query=query)
    if user is not None and not getattr(user, "is_superuser", False):
        qs = qs.filter(sender=user)
    return qs


def notification_templates_queryset(*, query="", template_type=""):
    qs = NotificationTemplate.objects.filter(is_deleted=False)
    if query:
        qs = qs.filter(Q(name__icontains=query) | Q(subject__icontains=query) | Q(body__icontains=query))
    if template_type:
        qs = qs.filter(template_type=template_type)
    return qs.order_by("template_type", "name")


def notification_metrics(user=None):
    messages = NotificationMessage.objects.filter(is_deleted=False)
    recipients = NotificationRecipient.objects.all()
    if user is not None and not getattr(user, "is_superuser", False):
        branch_ids = accessible_branch_ids(user, permission_codes=("notifications.send",))
        if branch_ids is not None:
            messages = messages.filter(Q(branch_id__in=branch_ids) | Q(sender=user) | Q(recipients__user=user)).distinct()
        recipients = recipients.filter(user=user)
    return {
        "sent_messages": messages.filter(status=NotificationMessage.Status.SENT).count(),
        "urgent_messages": messages.filter(priority=NotificationMessage.Priority.URGENT, status=NotificationMessage.Status.SENT).count(),
        "unread_for_user": recipients.filter(status=NotificationRecipient.DeliveryStatus.UNREAD).count(),
        "templates": NotificationTemplate.objects.filter(is_deleted=False, is_active=True).count(),
    }


def campaigns_queryset(*, user, permission_code="campaigns.view"):
    return scope_queryset_to_user_branches(
        Campaign.objects.filter(is_deleted=False).select_related("branch", "brand", "vehicle_model", "template", "created_by", "reviewed_by", "confirmed_by", "notification"),
        user=user,
        permission_codes=(permission_code,),
    ).order_by("-created_at")


def campaign_detail_queryset(*, user, permission_code="campaigns.view"):
    return campaigns_queryset(user=user, permission_code=permission_code).prefetch_related("recipient_snapshots")
