"""ES: Este módulo implementa servicios de negocio y efectos transaccionales para el dominio de notificaciones.

EN: This module implements business services and transactional effects for the notifications domain.

Contexto existente / Existing context:
Transactional business services for the notifications domain.
"""

from __future__ import annotations

import re
from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import OuterRef, Q, Subquery
from django.utils import timezone

from apps.audit.services import audit_log
from apps.accounts.scopes import accessible_branch_ids, accessible_users_queryset
from apps.common.modules import is_module_enabled
from apps.customers.models import Customer
from apps.notifications.models import Campaign, CampaignRecipient, CustomerNotificationPreference, NotificationMessage, NotificationRecipient, NotificationTemplate
from apps.privacy.models import ConsentRecord
from apps.sales.models import SaleRecord


def _message_snapshot(message: NotificationMessage):
    return {
        "title": message.title,
        "message_type": message.message_type,
        "priority": message.priority,
        "status": message.status,
        "branch_id": message.branch_id,
        "related_customer_id": message.related_customer_id,
        "related_vehicle_id": message.related_vehicle_id,
        "related_sale_id": message.related_sale_id,
        "related_document_id": message.related_document_id,
    }


def _template_snapshot(template: NotificationTemplate):
    return {"name": template.name, "template_type": template.template_type, "subject": template.subject, "is_active": template.is_active}


def _user_display_name(user):
    return user.get_full_name() or user.username or user.email


def _customer_display_name(customer):
    return customer.display_name or customer.email or customer.identification_number or f"Cliente #{customer.pk}"


@transaction.atomic
def create_notification_message(*, actor, form, dedup_key="") -> NotificationMessage:
    """Persist one message and its authorized recipients atomically."""

    users = list(form.cleaned_data.get("recipient_users") or [])
    customers = list(form.cleaned_data.get("recipient_customers") or [])
    if not users and not customers:
        raise ValidationError("Selecciona al menos un usuario interno o cliente destinatario.")
    branch_ids = accessible_branch_ids(actor, permission_codes=("notifications.send",))
    branch = form.cleaned_data.get("branch")
    if branch_ids is not None:
        if not branch or branch.pk not in branch_ids:
            raise ValidationError("Selecciona una sucursal autorizada para enviar la notificación.")
        if any(customer.assigned_branch_id != branch.pk for customer in customers):
            raise ValidationError("Los clientes destinatarios deben pertenecer a la sucursal seleccionada.")
        allowed_user_ids = set(accessible_users_queryset(actor, permission_codes=("notifications.send",)).values_list("pk", flat=True))
        if any(user.pk not in allowed_user_ids for user in users):
            raise ValidationError("Uno o más usuarios destinatarios están fuera de tu alcance.")
        related_branch_ids = [
            getattr(form.cleaned_data.get("related_customer"), "assigned_branch_id", None),
            getattr(form.cleaned_data.get("related_vehicle"), "branch_id", None),
            getattr(form.cleaned_data.get("related_sale"), "branch_id", None),
            getattr(form.cleaned_data.get("related_document"), "branch_id", None),
        ]
        if any(related_branch_id not in {None, branch.pk} for related_branch_id in related_branch_ids):
            raise ValidationError("Los registros relacionados deben pertenecer a la sucursal seleccionada.")
    dedup_key = (dedup_key or "").strip()
    if dedup_key:
        existing = NotificationMessage.objects.select_for_update().filter(dedup_key=dedup_key).first()
        if existing:
            if branch_ids is not None and existing.branch_id not in branch_ids:
                raise PermissionDenied("La notificación idempotente está fuera de tu alcance.")
            return existing
    message = form.save(commit=False)
    message.sender = actor if getattr(actor, "is_authenticated", False) else None
    message.created_by = actor if getattr(actor, "is_authenticated", False) else None
    message.status = NotificationMessage.Status.SENT
    message.dedup_key = dedup_key
    if not message.sent_at:
        message.sent_at = timezone.now()
    try:
        with transaction.atomic():
            message.save()
    except IntegrityError:
        if dedup_key:
            existing = NotificationMessage.objects.filter(dedup_key=dedup_key).first()
            if existing:
                if branch_ids is not None and existing.branch_id not in branch_ids:
                    raise PermissionDenied("La notificación idempotente está fuera de tu alcance.")
                return existing
        raise
    recipients = []
    for user in users:
        recipients.append(
            NotificationRecipient(
                notification=message,
                recipient_type=NotificationRecipient.RecipientType.USER,
                user=user,
                display_name_snapshot=_user_display_name(user),
                email_snapshot=user.email or "",
            )
        )
    for customer in customers:
        recipients.append(
            NotificationRecipient(
                notification=message,
                recipient_type=NotificationRecipient.RecipientType.CUSTOMER,
                customer=customer,
                display_name_snapshot=_customer_display_name(customer),
                email_snapshot=customer.email or "",
            )
        )
    NotificationRecipient.objects.bulk_create(recipients, ignore_conflicts=True)
    audit_log(user=actor, action="notifications.message.send", target=message, after={**_message_snapshot(message), "recipients": len(recipients)})
    return message


@transaction.atomic
def mark_recipient_read(*, actor, recipient: NotificationRecipient) -> NotificationRecipient:
    if recipient.status != NotificationRecipient.DeliveryStatus.READ:
        before = {"status": recipient.status, "read_at": recipient.read_at.isoformat() if recipient.read_at else None}
        recipient.status = NotificationRecipient.DeliveryStatus.READ
        recipient.read_at = timezone.now()
        recipient.save(update_fields=["status", "read_at", "updated_at"])
        audit_log(user=actor, action="notifications.recipient.read", target=recipient.notification, before=before, after={"status": recipient.status, "read_at": recipient.read_at.isoformat()})
    return recipient


@transaction.atomic
def archive_recipient(*, actor, recipient: NotificationRecipient) -> NotificationRecipient:
    before = {"status": recipient.status}
    recipient.status = NotificationRecipient.DeliveryStatus.ARCHIVED
    recipient.archived_at = timezone.now()
    recipient.save(update_fields=["status", "archived_at", "updated_at"])
    audit_log(user=actor, action="notifications.recipient.archive", target=recipient.notification, before=before, after={"status": recipient.status})
    return recipient


@transaction.atomic
def create_customer_event_notification(
    *,
    customer: Customer,
    title: str,
    body: str,
    message_type: str,
    dedup_key: str,
    actor=None,
    priority=NotificationMessage.Priority.NORMAL,
    branch=None,
    related_vehicle=None,
    related_sale=None,
    related_document=None,
):
    """Create one portal event per stable key, respecting customer preferences."""
    account = customer.account
    if account is None or not account.is_active:
        return None
    preference, _ = CustomerNotificationPreference.objects.get_or_create(customer=customer)
    if not preference.allows(message_type):
        return None
    dedup_key = (dedup_key or "").strip()
    if not dedup_key:
        raise ValidationError("La notificación de evento requiere una clave idempotente.")
    existing = NotificationMessage.objects.filter(dedup_key=dedup_key).first()
    if existing:
        return existing
    try:
        with transaction.atomic():
            message = NotificationMessage.objects.create(
                title=title[:180],
                body=body,
                message_type=message_type,
                priority=priority,
                status=NotificationMessage.Status.SENT,
                sender=actor if getattr(actor, "is_authenticated", False) else None,
                branch=branch or customer.assigned_branch,
                related_customer=customer,
                related_vehicle=related_vehicle,
                related_sale=related_sale,
                related_document=related_document,
                dedup_key=dedup_key,
                created_by=actor if getattr(actor, "is_authenticated", False) else None,
            )
    except IntegrityError:
        return NotificationMessage.objects.get(dedup_key=dedup_key)
    NotificationRecipient.objects.create(
        notification=message,
        recipient_type=NotificationRecipient.RecipientType.CUSTOMER,
        customer=customer,
        display_name_snapshot=_customer_display_name(customer),
        email_snapshot=customer.email or "",
    )
    audit_log(
        user=actor,
        action="notifications.customer_event.create",
        target=message,
        customer=customer,
        after={**_message_snapshot(message), "dedup_key": dedup_key},
    )
    return message


def schedule_customer_event_notification(**event):
    """Publish an in-app customer event only after its business transaction commits."""
    transaction.on_commit(
        lambda: create_customer_event_notification(**event),
        robust=True,
    )


@transaction.atomic
def mark_all_customer_recipients_read(*, actor, customer: Customer) -> int:
    now = timezone.now()
    owned = Q(
        recipient_type=NotificationRecipient.RecipientType.CUSTOMER,
        customer=customer,
    )
    if customer.account_id:
        owned |= Q(
            recipient_type=NotificationRecipient.RecipientType.USER,
            user_id=customer.account_id,
        )
    updated = NotificationRecipient.objects.filter(
        owned,
        status=NotificationRecipient.DeliveryStatus.UNREAD,
        notification__is_deleted=False,
        notification__status=NotificationMessage.Status.SENT,
    ).update(
        status=NotificationRecipient.DeliveryStatus.READ,
        read_at=now,
        updated_at=now,
    )
    if updated:
        audit_log(
            user=actor,
            action="notifications.customer_recipients.read_all",
            target=customer,
            customer=customer,
            metadata={"updated": updated},
        )
    return updated


@transaction.atomic
def update_customer_notification_preferences(*, actor, customer: Customer, form):
    preference, _ = CustomerNotificationPreference.objects.select_for_update().get_or_create(customer=customer)
    before = {
        field: getattr(preference, field)
        for field in ("invoice_updates", "document_updates", "service_updates", "general_alerts", "email_enabled")
    }
    for field in before:
        setattr(preference, field, form.cleaned_data[field])
    preference.save(update_fields=[*before.keys(), "updated_at"])
    audit_log(
        user=actor,
        action="notifications.customer_preferences.update",
        target=customer,
        customer=customer,
        before=before,
        after={field: getattr(preference, field) for field in before},
    )
    return preference


@transaction.atomic
def archive_message(*, actor, message: NotificationMessage) -> NotificationMessage:
    before = _message_snapshot(message)
    message.status = NotificationMessage.Status.ARCHIVED
    message.is_deleted = True
    message.deleted_at = timezone.now()
    message.save(update_fields=["status", "is_deleted", "deleted_at", "updated_at"])
    audit_log(user=actor, action="notifications.message.archive", target=message, before=before, after={"status": message.status, "is_deleted": True})
    return message


@transaction.atomic
def create_notification_template(*, actor, form) -> NotificationTemplate:
    template = form.save(commit=False)
    template.created_by = actor if getattr(actor, "is_authenticated", False) else None
    template.save()
    audit_log(user=actor, action="notifications.template.create", target=template, after=_template_snapshot(template))
    return template


@transaction.atomic
def update_notification_template(*, actor, template: NotificationTemplate, form) -> NotificationTemplate:
    before = _template_snapshot(template)
    template = form.save()
    audit_log(user=actor, action="notifications.template.update", target=template, before=before, after=_template_snapshot(template))
    return template


@transaction.atomic
def archive_notification_template(*, actor, template: NotificationTemplate) -> NotificationTemplate:
    before = _template_snapshot(template)
    template.is_active = False
    template.soft_delete()
    audit_log(user=actor, action="notifications.template.archive", target=template, before=before, after={"is_active": False, "is_deleted": True})
    return template


CAMPAIGN_VARIABLES = {"customer_name", "branch_name", "campaign_name"}
MAX_CAMPAIGN_RECIPIENTS = 10_000


def _validate_campaign_text(value):
    variables = set(re.findall(r"{([a-zA-Z_][a-zA-Z0-9_]*)}", value or ""))
    unsupported = variables - CAMPAIGN_VARIABLES
    remainder = value or ""
    for variable in variables:
        remainder = remainder.replace(f"{{{variable}}}", "")
    if unsupported or "{" in remainder or "}" in remainder:
        raise ValidationError("La plantilla contiene variables no permitidas.")


def render_campaign_text(*, text, campaign, customer_name):
    _validate_campaign_text(text)
    values = {
        "customer_name": customer_name,
        "branch_name": campaign.branch.name,
        "campaign_name": campaign.name,
    }
    rendered = text
    for variable, value in values.items():
        rendered = rendered.replace(f"{{{variable}}}", value or "")
    return rendered


def _locked_campaign(*, actor, campaign, permission_code):
    locked = Campaign.objects.select_for_update().select_related("branch").get(pk=campaign.pk, is_deleted=False)
    branch_ids = accessible_branch_ids(actor, permission_codes=(permission_code,))
    if branch_ids is not None and locked.branch_id not in branch_ids:
        raise PermissionDenied("La campaña está fuera de tu alcance de sucursal.")
    return locked


@transaction.atomic
def create_campaign(*, actor, form):
    campaign = form.save(commit=False)
    branch_ids = accessible_branch_ids(actor, permission_codes=("campaigns.manage",))
    if branch_ids is not None and campaign.branch_id not in branch_ids:
        raise PermissionDenied("La campaña está fuera de tu alcance de sucursal.")
    campaign.created_by = actor
    campaign.status = Campaign.Status.DRAFT
    campaign.save()
    audit_log(user=actor, action="campaigns.create", target=campaign, branch=campaign.branch, after={"segment_type": campaign.segment_type})
    return campaign


def _with_current_campaign_consent(customers, campaign):
    latest_consent = ConsentRecord.objects.filter(
        customer_id=OuterRef("pk"), purpose=campaign.consent_purpose
    ).order_by("-accepted_at", "-created_at")
    return customers.annotate(
        latest_campaign_consent=Subquery(latest_consent.values("status")[:1])
    ).filter(latest_campaign_consent=ConsentRecord.Status.GRANTED)


def _campaign_customers(campaign):
    customers = _with_current_campaign_consent(
        Customer.objects.filter(is_deleted=False, assigned_branch=campaign.branch), campaign
    )
    if campaign.segment_type == Campaign.SegmentType.RECENT:
        customers = customers.filter(updated_at__gte=timezone.now() - timedelta(days=campaign.inactivity_days))
    elif campaign.segment_type == Campaign.SegmentType.INACTIVE:
        cutoff = timezone.now() - timedelta(days=campaign.inactivity_days)
        customers = customers.filter(Q(status=Customer.Status.INACTIVE) | Q(updated_at__lt=cutoff))
    elif campaign.segment_type == Campaign.SegmentType.BUYERS:
        customers = customers.filter(sales__status=SaleRecord.Status.SOLD, sales__is_deleted=False)
    elif campaign.segment_type == Campaign.SegmentType.BRAND:
        customers = customers.filter(
            Q(sales__vehicle__brand=campaign.brand, sales__status=SaleRecord.Status.SOLD, sales__is_deleted=False)
            | Q(vehicle_interests__vehicle__brand=campaign.brand)
            | Q(vehicle_interests__brand__iexact=campaign.brand.name)
        )
    elif campaign.segment_type == Campaign.SegmentType.MODEL:
        customers = customers.filter(
            Q(sales__vehicle__model=campaign.vehicle_model, sales__status=SaleRecord.Status.SOLD, sales__is_deleted=False)
            | Q(vehicle_interests__vehicle__model=campaign.vehicle_model)
            | Q(vehicle_interests__model_name__iexact=campaign.vehicle_model.name)
        )
    elif campaign.segment_type == Campaign.SegmentType.CREATED_RANGE:
        customers = customers.filter(created_at__date__range=(campaign.customer_created_from, campaign.customer_created_to))
    elif campaign.segment_type == Campaign.SegmentType.SERVICE:
        if not is_module_enabled("post_sales"):
            raise ValidationError("El segmento de postventa no está disponible porque el módulo está desactivado.")
        customers = customers.filter(service_orders__is_deleted=False)
    return customers.distinct().order_by("pk")


@transaction.atomic
def calculate_campaign_recipients(*, actor, campaign):
    campaign = _locked_campaign(actor=actor, campaign=campaign, permission_code="campaigns.manage")
    if campaign.status != Campaign.Status.DRAFT:
        raise ValidationError("Solo una campaña en borrador puede calcular destinatarios.")
    customers = _campaign_customers(campaign)
    count = customers.count()
    if not count:
        raise ValidationError("El segmento no produjo destinatarios.")
    if count > MAX_CAMPAIGN_RECIPIENTS:
        raise ValidationError(f"El segmento supera el límite de {MAX_CAMPAIGN_RECIPIENTS} destinatarios.")
    CampaignRecipient.objects.bulk_create(
        [
            CampaignRecipient(
                campaign=campaign,
                customer=customer,
                display_name_snapshot=customer.display_name,
                email_snapshot=customer.email or "",
                phone_snapshot=customer.phone or customer.whatsapp or "",
            )
            for customer in customers
        ]
    )
    campaign.recipient_count = count
    campaign.calculated_at = timezone.now()
    campaign.status = Campaign.Status.REVIEW
    campaign.save(update_fields=["recipient_count", "calculated_at", "status", "updated_at"])
    audit_log(user=actor, action="campaigns.recipients_calculated", target=campaign, branch=campaign.branch, after={"recipient_count": count})
    return campaign


@transaction.atomic
def prepare_campaign_message(*, actor, campaign, form):
    campaign = _locked_campaign(actor=actor, campaign=campaign, permission_code="campaigns.manage")
    if campaign.status != Campaign.Status.REVIEW:
        raise ValidationError("La campaña debe tener destinatarios calculados antes de preparar el mensaje.")
    template = form.cleaned_data.get("template")
    subject = (form.cleaned_data.get("subject") or (template.subject if template else "")).strip()
    body = (form.cleaned_data.get("body") or (template.body if template else "")).strip()
    if not subject or not body:
        raise ValidationError("Define asunto y mensaje, directamente o mediante una plantilla.")
    _validate_campaign_text(subject)
    _validate_campaign_text(body)
    campaign.template = template
    campaign.subject = subject
    campaign.body = body
    campaign.channel = form.cleaned_data["channel"]
    campaign.reviewed_by = actor
    campaign.reviewed_at = timezone.now()
    campaign.status = Campaign.Status.READY
    campaign.save(update_fields=["template", "subject", "body", "channel", "reviewed_by", "reviewed_at", "status", "updated_at"])
    audit_log(user=actor, action="campaigns.message_prepared", target=campaign, branch=campaign.branch, after={"channel": campaign.channel})
    return campaign


def _deliver_campaign_in_app(*, campaign, recipients, actor):
    message = NotificationMessage.objects.create(
        title=render_campaign_text(text=campaign.subject, campaign=campaign, customer_name="Cliente")[:180],
        body=render_campaign_text(text=campaign.body, campaign=campaign, customer_name="Cliente"),
        message_type=NotificationMessage.MessageType.MESSAGE,
        priority=NotificationMessage.Priority.NORMAL,
        status=NotificationMessage.Status.SENT,
        sender=actor,
        template=campaign.template,
        branch=campaign.branch,
        dedup_key=f"campaign:{campaign.pk}:confirmed",
        created_by=actor,
    )
    NotificationRecipient.objects.bulk_create(
        [
            NotificationRecipient(
                notification=message,
                recipient_type=NotificationRecipient.RecipientType.CUSTOMER,
                customer=recipient.customer,
                display_name_snapshot=recipient.display_name_snapshot,
                email_snapshot=recipient.email_snapshot,
            )
            for recipient in recipients
        ]
    )
    return message


CAMPAIGN_CHANNEL_HANDLERS = {Campaign.Channel.IN_APP: _deliver_campaign_in_app}


@transaction.atomic
def confirm_campaign(*, actor, campaign):
    campaign = _locked_campaign(actor=actor, campaign=campaign, permission_code="campaigns.send")
    if campaign.status == Campaign.Status.SENT:
        return campaign
    if campaign.status != Campaign.Status.READY:
        raise ValidationError("La campaña debe estar revisada y lista antes de confirmarla.")
    recipient_qs = campaign.recipient_snapshots.select_related("customer")
    snapshot_customer_ids = recipient_qs.values_list("customer_id", flat=True)
    consented_customer_ids = _with_current_campaign_consent(
        Customer.objects.filter(is_deleted=False, pk__in=snapshot_customer_ids), campaign
    ).values("pk")
    recipient_qs.exclude(customer_id__in=consented_customer_ids).delete()
    recipients = list(recipient_qs)
    if not recipients:
        campaign.recipient_count = 0
        campaign.status = Campaign.Status.CANCELLED
        campaign.save(update_fields=["recipient_count", "status", "updated_at"])
        audit_log(user=actor, action="campaigns.cancelled_no_consent", target=campaign, branch=campaign.branch)
        return campaign
    if campaign.recipient_count != len(recipients):
        campaign.recipient_count = len(recipients)
        campaign.save(update_fields=["recipient_count", "updated_at"])
    rendered_at = timezone.now()
    for recipient in recipients:
        recipient.rendered_subject = render_campaign_text(text=campaign.subject, campaign=campaign, customer_name=recipient.display_name_snapshot)[:180]
        recipient.rendered_body = render_campaign_text(text=campaign.body, campaign=campaign, customer_name=recipient.display_name_snapshot)
        recipient.updated_at = rendered_at
    CampaignRecipient.objects.bulk_update(recipients, ["rendered_subject", "rendered_body", "updated_at"])
    handler = CAMPAIGN_CHANNEL_HANDLERS.get(campaign.channel)
    if not handler:
        raise ValidationError("El canal seleccionado no está configurado.")
    message = handler(campaign=campaign, recipients=recipients, actor=actor)
    campaign.notification = message
    campaign.confirmed_by = actor
    campaign.confirmed_at = timezone.now()
    campaign.status = Campaign.Status.SENT
    campaign.save(update_fields=["notification", "confirmed_by", "confirmed_at", "status", "updated_at"])
    audit_log(user=actor, action="campaigns.confirmed", target=campaign, branch=campaign.branch, after={"notification_id": message.pk, "recipient_count": len(recipients)})
    return campaign
