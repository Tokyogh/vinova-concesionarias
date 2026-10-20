"""ES: Este módulo define modelos persistentes, estados y restricciones para el dominio de notificaciones.

EN: This module defines persistent models, states, and constraints for the notifications domain.

Contexto existente / Existing context:
Persistent domain models and database constraints for the notifications domain.
"""

from __future__ import annotations

from django.db import models
from django.utils import timezone

from apps.common.models import SoftDeleteModel, TimeStampedModel


class NotificationTemplate(TimeStampedModel, SoftDeleteModel):
    """Plantilla reutilizable para mensajes internos.

    Permite que personal no técnico prepare textos estándar desde la web sin
    editar HTML, código ni archivos del proyecto.
    """

    class TemplateType(models.TextChoices):
        GENERAL = "general", "General"
        SALE = "sale", "Venta / cotización"
        DOCUMENT = "document", "Documento"
        MAINTENANCE = "maintenance", "Mantenimiento"
        CUSTOMER_SERVICE = "customer_service", "Atención al cliente"
        SYSTEM = "system", "Sistema"

    name = models.CharField(max_length=140, unique=True, db_index=True)
    template_type = models.CharField(max_length=30, choices=TemplateType.choices, default=TemplateType.GENERAL, db_index=True)
    subject = models.CharField(max_length=180)
    body = models.TextField(help_text="Texto base. Puede contener variables documentadas en la interfaz.")
    is_active = models.BooleanField(default=True, db_index=True)
    created_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="created_notification_templates")

    class Meta:
        ordering = ["template_type", "name"]
        indexes = [models.Index(fields=["template_type", "is_active"])]
        verbose_name = "Plantilla de notificación"
        verbose_name_plural = "Plantillas de notificación"

    def __str__(self):
        return self.name


class NotificationMessage(TimeStampedModel, SoftDeleteModel):
    """Mensaje interno enviado a usuarios y/o clientes.

    Un único mensaje puede tener muchos destinatarios. Las lecturas se guardan
    en NotificationRecipient para mantener trazabilidad individual.
    """

    class MessageType(models.TextChoices):
        MESSAGE = "message", "Mensaje"
        ALERT = "alert", "Alerta"
        INVOICE = "invoice", "Factura"
        DOCUMENT = "document", "Documento"
        MAINTENANCE = "maintenance", "Mantenimiento"
        SYSTEM = "system", "Sistema"

    class Priority(models.TextChoices):
        NORMAL = "normal", "Normal"
        HIGH = "high", "Alta"
        URGENT = "urgent", "Urgente"

    class Status(models.TextChoices):
        DRAFT = "draft", "Borrador"
        SENT = "sent", "Enviado"
        ARCHIVED = "archived", "Archivado"

    title = models.CharField(max_length=180, db_index=True)
    body = models.TextField()
    message_type = models.CharField(max_length=30, choices=MessageType.choices, default=MessageType.MESSAGE, db_index=True)
    priority = models.CharField(max_length=20, choices=Priority.choices, default=Priority.NORMAL, db_index=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.SENT, db_index=True)
    sender = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="sent_notifications")
    template = models.ForeignKey(NotificationTemplate, null=True, blank=True, on_delete=models.SET_NULL, related_name="messages")
    branch = models.ForeignKey("branches.Branch", null=True, blank=True, on_delete=models.SET_NULL, related_name="notifications")
    related_customer = models.ForeignKey("customers.Customer", null=True, blank=True, on_delete=models.SET_NULL, related_name="notifications")
    related_vehicle = models.ForeignKey("vehicles.Vehicle", null=True, blank=True, on_delete=models.SET_NULL, related_name="notifications")
    related_sale = models.ForeignKey("sales.SaleRecord", null=True, blank=True, on_delete=models.SET_NULL, related_name="notifications")
    related_document = models.ForeignKey("documents.PrivateDocument", null=True, blank=True, on_delete=models.SET_NULL, related_name="notifications")
    dedup_key = models.CharField(max_length=160, blank=True, db_index=True)
    sent_at = models.DateTimeField(default=timezone.now, db_index=True)
    created_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="created_notifications")

    class Meta:
        ordering = ["-sent_at", "-created_at"]
        indexes = [
            models.Index(fields=["status", "priority"]),
            models.Index(fields=["message_type", "sent_at"]),
            models.Index(fields=["branch", "sent_at"]),
            models.Index(fields=["sender", "sent_at"]),
            models.Index(fields=["sent_at"]),
        ]
        constraints = [
            models.UniqueConstraint(fields=["dedup_key"], condition=~models.Q(dedup_key=""), name="unique_notification_dedup_key"),
        ]
        verbose_name = "Notificación"
        verbose_name_plural = "Notificaciones"

    def __str__(self):
        return self.title

    @property
    def recipient_count(self):
        return self.recipients.count()


class NotificationRecipient(TimeStampedModel):
    class RecipientType(models.TextChoices):
        USER = "user", "Usuario interno"
        CUSTOMER = "customer", "Cliente"

    class DeliveryStatus(models.TextChoices):
        UNREAD = "unread", "No leído"
        READ = "read", "Leído"
        ARCHIVED = "archived", "Archivado"

    notification = models.ForeignKey(NotificationMessage, on_delete=models.CASCADE, related_name="recipients")
    recipient_type = models.CharField(max_length=20, choices=RecipientType.choices, db_index=True)
    user = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.CASCADE, related_name="notification_recipients")
    customer = models.ForeignKey("customers.Customer", null=True, blank=True, on_delete=models.CASCADE, related_name="notification_recipients")
    display_name_snapshot = models.CharField(max_length=180, blank=True)
    email_snapshot = models.EmailField(blank=True)
    status = models.CharField(max_length=20, choices=DeliveryStatus.choices, default=DeliveryStatus.UNREAD, db_index=True)
    read_at = models.DateTimeField(null=True, blank=True, db_index=True)
    archived_at = models.DateTimeField(null=True, blank=True, db_index=True)

    class Meta:
        ordering = ["-notification__sent_at", "id"]
        constraints = [
            models.UniqueConstraint(fields=["notification", "user"], condition=models.Q(user__isnull=False), name="unique_notification_user_recipient"),
            models.UniqueConstraint(fields=["notification", "customer"], condition=models.Q(customer__isnull=False), name="unique_notification_customer_recipient"),
        ]
        indexes = [
            models.Index(fields=["recipient_type", "status"]),
            models.Index(fields=["user", "status"]),
            models.Index(fields=["customer", "status"]),
            models.Index(fields=["read_at"]),
        ]
        verbose_name = "Destinatario de notificación"
        verbose_name_plural = "Destinatarios de notificación"

    def __str__(self):
        return f"{self.notification.title} → {self.display_name_snapshot or self.user or self.customer}"

    @property
    def is_read(self):
        return self.status == self.DeliveryStatus.READ


class CustomerNotificationPreference(TimeStampedModel):
    customer = models.OneToOneField(
        "customers.Customer",
        on_delete=models.CASCADE,
        related_name="notification_preference",
    )
    invoice_updates = models.BooleanField(default=True)
    document_updates = models.BooleanField(default=True)
    service_updates = models.BooleanField(default=True)
    general_alerts = models.BooleanField(default=True)
    email_enabled = models.BooleanField(
        default=False,
        help_text="Reserva la preferencia; no activa envíos externos sin un proveedor configurado.",
    )

    class Meta:
        verbose_name = "Preferencia de notificaciones de cliente"
        verbose_name_plural = "Preferencias de notificaciones de clientes"

    def __str__(self):
        return f"Preferencias de {self.customer.display_name}"

    def allows(self, message_type: str) -> bool:
        mapping = {
            NotificationMessage.MessageType.INVOICE: self.invoice_updates,
            NotificationMessage.MessageType.DOCUMENT: self.document_updates,
            NotificationMessage.MessageType.MAINTENANCE: self.service_updates,
            NotificationMessage.MessageType.ALERT: self.general_alerts,
            NotificationMessage.MessageType.SYSTEM: self.general_alerts,
        }
        return mapping.get(message_type, self.general_alerts)


class Campaign(TimeStampedModel, SoftDeleteModel):
    class Status(models.TextChoices):
        DRAFT = "draft", "Borrador"
        REVIEW = "review", "En revisión"
        READY = "ready", "Lista para confirmar"
        SENT = "sent", "Enviada"
        CANCELLED = "cancelled", "Cancelada"

    class SegmentType(models.TextChoices):
        ALL = "all", "Todos los clientes"
        RECENT = "recent", "Actividad reciente"
        INACTIVE = "inactive", "Clientes inactivos"
        BUYERS = "buyers", "Compradores"
        BRAND = "brand", "Interés o compra por marca"
        MODEL = "model", "Interés o compra por modelo"
        CREATED_RANGE = "created_range", "Alta en rango de fechas"
        SERVICE = "service", "Clientes de postventa"

    class Channel(models.TextChoices):
        IN_APP = "in_app", "Notificación registrada"

    class ConsentPurpose(models.TextChoices):
        MARKETING = "marketing", "Marketing"
        COMMERCIAL_CONTACT = "commercial_contact", "Contacto comercial"

    name = models.CharField(max_length=160, db_index=True)
    branch = models.ForeignKey("branches.Branch", on_delete=models.PROTECT, related_name="notification_campaigns")
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True)
    segment_type = models.CharField(max_length=30, choices=SegmentType.choices, default=SegmentType.ALL, db_index=True)
    inactivity_days = models.PositiveSmallIntegerField(default=90)
    brand = models.ForeignKey("vehicles.VehicleBrand", null=True, blank=True, on_delete=models.PROTECT, related_name="notification_campaigns")
    vehicle_model = models.ForeignKey("vehicles.VehicleModel", null=True, blank=True, on_delete=models.PROTECT, related_name="notification_campaigns")
    customer_created_from = models.DateField(null=True, blank=True)
    customer_created_to = models.DateField(null=True, blank=True)
    template = models.ForeignKey(NotificationTemplate, null=True, blank=True, on_delete=models.SET_NULL, related_name="campaigns")
    subject = models.CharField(max_length=180, blank=True)
    body = models.TextField(blank=True)
    channel = models.CharField(max_length=20, choices=Channel.choices, default=Channel.IN_APP)
    consent_purpose = models.CharField(max_length=32, choices=ConsentPurpose.choices, default=ConsentPurpose.MARKETING)
    recipient_count = models.PositiveIntegerField(default=0)
    calculated_at = models.DateTimeField(null=True, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="created_campaigns")
    reviewed_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="reviewed_campaigns")
    confirmed_by = models.ForeignKey("accounts.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="confirmed_campaigns")
    notification = models.OneToOneField(NotificationMessage, null=True, blank=True, on_delete=models.SET_NULL, related_name="campaign")

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["branch", "status"]), models.Index(fields=["segment_type", "created_at"])]

    def __str__(self):
        return self.name


class CampaignRecipient(TimeStampedModel):
    campaign = models.ForeignKey(Campaign, on_delete=models.CASCADE, related_name="recipient_snapshots")
    customer = models.ForeignKey("customers.Customer", null=True, blank=True, on_delete=models.SET_NULL, related_name="campaign_snapshots")
    display_name_snapshot = models.CharField(max_length=180)
    email_snapshot = models.EmailField(blank=True)
    phone_snapshot = models.CharField(max_length=30, blank=True)
    rendered_subject = models.CharField(max_length=180, blank=True)
    rendered_body = models.TextField(blank=True)

    class Meta:
        ordering = ["id"]
        constraints = [models.UniqueConstraint(fields=["campaign", "customer"], name="unique_campaign_customer_snapshot")]
        indexes = [models.Index(fields=["campaign", "created_at"])]

    def __str__(self):
        return f"{self.campaign} â†’ {self.display_name_snapshot}"
