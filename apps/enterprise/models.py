"""ES: Este módulo define modelos persistentes, estados y restricciones para el dominio de configuración empresarial.

EN: This module defines persistent models, states, and constraints for the enterprise domain.

Contexto existente / Existing context:
Persistent domain models and database constraints for the enterprise domain.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import models

from apps.common.models import TimeStampedModel


class CompanyPublicSettings(TimeStampedModel):
    """Configuración visual y pública de la empresa dueña de la instalación.

    No es multi-tenant. Existe para que una empresa edite su identidad, portada,
    contacto, textos legales y catálogo público desde la web sin tocar plantillas,
    archivos de raíz ni código.
    """

    company = models.OneToOneField("companies.Company", on_delete=models.CASCADE, related_name="public_settings")
    website = models.URLField(blank=True)
    whatsapp = models.CharField(max_length=40, blank=True)
    public_email = models.EmailField(blank=True)
    public_phone = models.CharField(max_length=40, blank=True)
    public_address = models.TextField(blank=True)
    opening_hours = models.TextField(blank=True)
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    linkedin_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True)

    hero_eyebrow = models.CharField(max_length=120, default="Concesionaria automotriz")
    hero_title = models.CharField(max_length=220, default="Encuentra vehículos, solicita información y conecta con la sucursal correcta.")
    hero_subtitle = models.TextField(default="Catálogo público profesional conectado con operación interna protegida para equipo autorizado.")
    hero_primary_label = models.CharField(max_length=80, default="Ver vehículos disponibles")
    hero_secondary_label = models.CharField(max_length=80, default="Solicitar atención")
    catalog_intro_title = models.CharField(max_length=160, default="Modelos destacados")
    catalog_intro_text = models.TextField(default="Presentación comercial clara para vehículos publicados y disponibles.")
    attention_title = models.CharField(max_length=160, default="Un flujo simple para clientes, completo para la empresa")
    attention_text = models.TextField(blank=True)
    footer_text = models.TextField(default="Plataforma web empresarial para operación automotriz y experiencia comercial de concesionaria.")

    show_public_branches = models.BooleanField(default=True)
    show_vehicle_prices = models.BooleanField(default=True)
    show_social_links = models.BooleanField(default=True)
    enable_public_contact_cta = models.BooleanField(default=True)
    allow_client_registration = models.BooleanField(
        default=False,
        help_text="Permite crear nuevas cuentas de cliente desde la web pública. No enlaza expedientes existentes.",
    )

    privacy_policy = models.TextField(blank=True)
    terms_and_conditions = models.TextField(blank=True)
    data_processing_summary = models.TextField(blank=True)

    class Meta:
        verbose_name = "Configuración pública empresarial"
        verbose_name_plural = "Configuraciones públicas empresariales"

    def __str__(self):
        return f"Configuración pública de {self.company.commercial_name}"


class ApprovalPolicy(TimeStampedModel):
    """Reglas configurables de aprobación.

    Evita que el sistema sea invasivo: acciones rutinarias pueden ser automáticas,
    mientras descuentos altos, cambios de precio, anulaciones, ajustes fuertes o
    eliminación permanente pueden requerir autorización según política de empresa.
    """

    class Action(models.TextChoices):
        PRICE_CHANGE = "price_change", "Cambio de precio de vehículo"
        DISCOUNT = "discount", "Descuento comercial"
        SALE_CONFIRMATION = "sale_confirmation", "Confirmación de venta"
        INVOICE_VOID = "invoice_void", "Anulación de comprobante"
        STOCK_ADJUSTMENT = "stock_adjustment", "Ajuste de stock"
        PERMANENT_DELETE = "permanent_delete", "Eliminación permanente"
        CRITICAL_STATUS_CHANGE = "critical_status_change", "Cambio de estado crítico"

    class Mode(models.TextChoices):
        AUTOMATIC = "automatic", "Automático"
        REQUIRE_APPROVAL = "require_approval", "Requiere aprobación"
        THRESHOLD = "threshold", "Solo si supera umbral"
        DISABLED = "disabled", "Desactivado"

    company = models.ForeignKey("companies.Company", on_delete=models.CASCADE, related_name="approval_policies")
    action = models.CharField(max_length=40, choices=Action.choices, db_index=True)
    mode = models.CharField(max_length=30, choices=Mode.choices, default=Mode.AUTOMATIC, db_index=True)
    threshold_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    threshold_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    applies_to_roles = models.ManyToManyField("accounts.Role", blank=True, related_name="approval_policies")
    requires_reason = models.BooleanField(default=True)
    notify_supervisors = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True, db_index=True)
    notes = models.TextField(blank=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["company", "action"], name="unique_approval_policy_per_company_action")]
        indexes = [models.Index(fields=["company", "action", "is_active"]), models.Index(fields=["mode", "is_active"])]
        ordering = ["action"]
        verbose_name = "Política de aprobación"
        verbose_name_plural = "Políticas de aprobación"

    def __str__(self):
        return f"{self.company.commercial_name} · {self.get_action_display()}"

    def requires_approval_for(self, *, amount: Decimal | None = None, percent: Decimal | None = None) -> bool:
        if not self.is_active or self.mode == self.Mode.DISABLED:
            return False
        if self.mode == self.Mode.REQUIRE_APPROVAL:
            return True
        if self.mode == self.Mode.AUTOMATIC:
            return False
        amount_exceeded = amount is not None and self.threshold_amount is not None and amount > self.threshold_amount
        percent_exceeded = percent is not None and self.threshold_percent is not None and percent > self.threshold_percent
        return bool(amount_exceeded or percent_exceeded)
