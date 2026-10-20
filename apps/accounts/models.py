"""ES: Este módulo define modelos persistentes, estados y restricciones para el dominio de cuentas.

EN: This module defines persistent models, states, and constraints for the accounts domain.

Contexto existente / Existing context:
Persistent domain models and database constraints for the accounts domain.
"""

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

from apps.accounts.storage import avatar_storage
from apps.common.models import TimeStampedModel
from apps.common.validators import validate_avatar_image


class PermissionCode(TimeStampedModel):
    module = models.CharField(max_length=80, db_index=True)
    code = models.CharField(max_length=120, unique=True, db_index=True)
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)

    class Meta:
        ordering = ["module", "code"]
        verbose_name = "Permiso"
        verbose_name_plural = "Permisos"

    def __str__(self):
        return self.code


class Role(TimeStampedModel):
    class RoleType(models.TextChoices):
        SYSTEM = "system", "Sistema"
        BUSINESS = "business", "Negocio"
        CUSTOM = "custom", "Personalizado"

    code = models.SlugField(max_length=80, unique=True, db_index=True)
    name = models.CharField(max_length=120)
    description = models.TextField(blank=True)
    role_type = models.CharField(max_length=20, choices=RoleType.choices, default=RoleType.BUSINESS)
    level = models.PositiveSmallIntegerField(default=50, help_text="Menor número = mayor autoridad")
    permissions = models.ManyToManyField(PermissionCode, blank=True, related_name="roles")
    is_active = models.BooleanField(default=True, db_index=True)

    class Meta:
        ordering = ["level", "name"]
        verbose_name = "Rol"
        verbose_name_plural = "Roles"

    def __str__(self):
        return self.name


class User(AbstractUser):
    """Represent an authenticated account and resolve its effective RBAC scope."""

    class AvatarProvider(models.TextChoices):
        LOCAL = "local", "Local"
        CLOUDINARY = "cloudinary", "Cloudinary"

    email = models.EmailField(unique=True, db_index=True)
    phone = models.CharField(max_length=30, blank=True)
    branch = models.ForeignKey("branches.Branch", null=True, blank=True, on_delete=models.SET_NULL, related_name="users")
    avatar = models.ImageField(
        upload_to="avatars/%Y/%m/",
        storage=avatar_storage,
        blank=True,
        validators=[validate_avatar_image],
    )
    avatar_provider = models.CharField(max_length=20, choices=AvatarProvider.choices, default=AvatarProvider.LOCAL)
    must_change_password = models.BooleanField(default=False)
    failed_login_count = models.PositiveSmallIntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    last_password_change_at = models.DateTimeField(null=True, blank=True)
    REQUIRED_FIELDS = ["email"]

    class Meta:
        indexes = [models.Index(fields=["email"]), models.Index(fields=["username"]), models.Index(fields=["is_active"])]
        verbose_name = "Usuario"
        verbose_name_plural = "Usuarios"

    @property
    def is_locked(self):
        return bool(self.locked_until and self.locked_until > timezone.now())

    @property
    def avatar_url(self):
        if not self.avatar or not self.avatar.name:
            return ""
        try:
            return self.avatar.url
        except ValueError:
            return ""

    @property
    def avatar_initials(self):
        source = self.get_full_name().strip() or self.username or "?"
        initials = "".join(part[0] for part in source.split()[:2]).upper()
        return initials or "?"

    def delete_avatar(self):
        if self.avatar and self.avatar.name:
            self.avatar.delete(save=False)
        self.avatar = ""
        self.avatar_provider = self.AvatarProvider.LOCAL

    def active_role_assignments(self):
        # Authentication normally rejects inactive accounts before a view runs,
        # but domain services also call this API directly. Keep the authorization
        # boundary deny-by-default even outside the request authentication flow.
        if not self.is_active:
            return self.user_roles.none()
        now = timezone.now()
        return self.user_roles.filter(is_active=True, role__is_active=True).filter(
            models.Q(starts_at__isnull=True) | models.Q(starts_at__lte=now),
            models.Q(expires_at__isnull=True) | models.Q(expires_at__gt=now),
        )

    def role_codes(self):
        return list(self.active_role_assignments().values_list("role__code", flat=True).distinct())

    def has_role(self, code):
        return code in self.role_codes()

    def has_perm_code(self, code, branch=None):
        if not self.is_active:
            return False
        if self.is_superuser:
            return True
        qs = self.active_role_assignments().filter(role__permissions__code=code)
        if branch is not None:
            qs = qs.filter(models.Q(branch=branch) | models.Q(branch__isnull=True))
        return qs.exists()

    @property
    def can_access_internal_panel(self):
        """True cuando el usuario tiene alcance operativo o administrativo.

        Sirve para separar la experiencia pública del área interna. Un cliente
        autenticado puede ver su perfil sin que se le muestre gestión de staff,
        roles, empresas, sucursales, ventas o reportes.
        """

        if self.is_superuser:
            return True
        return self.active_role_assignments().filter(
            role__permissions__code__in=[
                "dashboard.view",
                "accounts.manage_users",
                "companies.manage",
                "branches.manage",
                "vehicles.view",
                "vehicles.manage",
                "inventory.view",
                "customers.view",
                "sales.quote",
                "invoices.view",
                "invoices.issue",
                "invoices.manage",
                "invoices.void",
                "documents.view",
                "documents.manage",
                "documents.download_private",
                "notifications.view",
                "notifications.send",
                "notifications.manage_templates",
                "campaigns.view",
                "campaigns.manage",
                "campaigns.send",
                "reports.view",
                "imports.manage",
                "data.export",
                "enterprise.manage",
                "sri.manage",
                "approvals.manage",
                "audit.view",
                "audit.export",
                "audit.manage_alerts",
                "leads.view",
                "leads.manage",
                "analytics.view",
                "continuity.view",
                "continuity.manage",
                "continuity.restore",
                "privacy.view",
                "privacy.manage",
                "privacy.export",
                "privacy.anonymize",
                "security.view",
                "security.manage",
                "integrations.view",
                "integrations.manage",
                "help.view",
                "quality.view",
                "quality.run",
            ],
        ).exists()

    @property
    def can_access_portal(self):
        return self.has_perm_code("portal.access")

    @property
    def can_manage_users(self):
        return self.has_perm_code("accounts.manage_users")

    @property
    def can_manage_companies(self):
        return self.has_perm_code("companies.manage")

    @property
    def can_manage_branches(self):
        return self.has_perm_code("branches.manage")

    @property
    def can_view_internal_vehicles(self):
        return self.has_perm_code("vehicles.view") or self.has_perm_code("vehicles.manage")

    @property
    def can_manage_vehicles(self):
        return self.has_perm_code("vehicles.manage")

    @property
    def can_publish_vehicles(self):
        return self.has_perm_code("vehicles.publish")

    @property
    def can_view_inventory(self):
        return self.has_perm_code("inventory.view") or self.has_perm_code("inventory.manage_stock")

    @property
    def can_manage_inventory(self):
        return self.has_perm_code("inventory.manage_stock")

    @property
    def can_view_customers(self):
        return self.has_perm_code("customers.view") or self.has_perm_code("customers.manage")

    @property
    def can_manage_customers(self):
        return self.has_perm_code("customers.manage")

    @property
    def can_access_sales(self):
        return self.has_perm_code("sales.quote") or self.has_perm_code("sales.sell") or self.has_perm_code("sales.reserve")


    @property
    def can_manage_quotes(self):
        return self.has_perm_code("sales.quote")

    @property
    def can_manage_reservations(self):
        return self.has_perm_code("sales.reserve")

    @property
    def can_confirm_sales(self):
        return self.has_perm_code("sales.sell")

    @property
    def can_view_invoices(self):
        return self.has_perm_code("invoices.view") or self.has_perm_code("invoices.issue") or self.has_perm_code("invoices.manage")

    @property
    def can_issue_invoices(self):
        return self.has_perm_code("invoices.issue") or self.has_perm_code("invoices.manage")

    @property
    def can_manage_invoices(self):
        return self.has_perm_code("invoices.manage")

    @property
    def can_void_invoices(self):
        return self.has_perm_code("invoices.void") or self.has_perm_code("invoices.manage")


    @property
    def can_view_documents(self):
        return self.has_perm_code("documents.view") or self.has_perm_code("documents.manage") or self.has_perm_code("documents.download_private")

    @property
    def can_manage_documents(self):
        return self.has_perm_code("documents.manage")

    @property
    def can_download_private_documents(self):
        return self.has_perm_code("documents.download_private") or self.has_perm_code("documents.manage")

    @property
    def can_view_notifications(self):
        return self.has_perm_code("notifications.view") or self.has_perm_code("notifications.send")

    @property
    def can_send_notifications(self):
        return self.has_perm_code("notifications.send")

    @property
    def can_manage_notification_templates(self):
        return self.has_perm_code("notifications.manage_templates")


    @property
    def can_manage_enterprise_settings(self):
        return self.has_perm_code("enterprise.manage")

    @property
    def can_manage_sri_settings(self):
        return self.has_perm_code("sri.manage")

    @property
    def can_manage_approval_policies(self):
        return self.has_perm_code("approvals.manage")

    @property
    def can_view_reports(self):
        return self.has_perm_code("reports.view")

    @property
    def can_manage_imports(self):
        return self.has_perm_code("imports.manage")

    @property
    def can_export_data(self):
        return self.has_perm_code("data.export") or self.has_perm_code("reports.view")

    @property
    def can_view_audit(self):
        return self.has_perm_code("audit.view")

    @property
    def can_export_audit(self):
        return self.has_perm_code("audit.export")

    @property
    def can_manage_audit_alerts(self):
        return self.has_perm_code("audit.manage_alerts")

    @property
    def can_view_leads(self):
        return self.has_perm_code("leads.view")

    @property
    def can_manage_leads(self):
        return self.has_perm_code("leads.manage")

    @property
    def can_assign_leads(self):
        return self.has_perm_code("leads.assign")

    @property
    def can_export_leads(self):
        return self.has_perm_code("leads.export")

    @property
    def can_view_analytics(self):
        return self.has_perm_code("analytics.view")

    @property
    def can_export_analytics(self):
        return self.has_perm_code("analytics.export")

    @property
    def can_view_continuity(self):
        return self.has_perm_code("continuity.view")

    @property
    def can_manage_continuity(self):
        return self.has_perm_code("continuity.manage")

    @property
    def can_restore_continuity(self):
        return self.has_perm_code("continuity.restore")

    @property
    def can_view_privacy(self):
        return self.has_perm_code("privacy.view")

    @property
    def can_manage_privacy(self):
        return self.has_perm_code("privacy.manage")

    @property
    def can_export_privacy(self):
        return self.has_perm_code("privacy.export")

    @property
    def can_anonymize_privacy(self):
        return self.has_perm_code("privacy.anonymize")

    @property
    def can_view_security(self):
        return self.has_perm_code("security.view")

    @property
    def can_manage_security(self):
        return self.has_perm_code("security.manage")

    @property
    def can_approve_staff_access(self):
        return self.has_perm_code("security.approve_staff_access")

    @property
    def can_view_integrations(self):
        return self.has_perm_code("integrations.view") or self.has_perm_code("integrations.manage")

    @property
    def can_manage_integrations(self):
        return self.has_perm_code("integrations.manage")

    @property
    def can_view_quality(self):
        return self.has_perm_code("quality.view") or self.has_perm_code("quality.run")

    @property
    def can_run_quality(self):
        return self.has_perm_code("quality.run")

    @property
    def can_view_help(self):
        return self.has_perm_code("help.view") or self.has_perm_code("help.manage")

    @property
    def can_manage_help(self):
        return self.has_perm_code("help.manage")


class UserRole(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="user_roles")
    role = models.ForeignKey(Role, on_delete=models.PROTECT, related_name="user_roles")
    branch = models.ForeignKey("branches.Branch", null=True, blank=True, on_delete=models.CASCADE, related_name="user_roles")
    is_active = models.BooleanField(default=True, db_index=True)
    starts_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    assigned_by = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="assigned_roles")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["user", "role", "branch"], name="unique_user_role_per_branch")]
        indexes = [models.Index(fields=["user", "is_active"]), models.Index(fields=["role", "is_active"])]
        verbose_name = "Rol asignado"
        verbose_name_plural = "Roles asignados"

    def __str__(self):
        return f"{self.user} - {self.role}"


class ClientInvitation(TimeStampedModel):
    """Token persistente y de un solo uso para acceso de clientes."""

    class Kind(models.TextChoices):
        STAFF_INVITATION = "staff_invitation", "Invitación de la concesionaria"
        REGISTRATION_ACTIVATION = "registration_activation", "Activación de registro"

    class Status(models.TextChoices):
        PENDING = "pending", "Pendiente"
        ACCEPTED = "accepted", "Aceptada"
        REVOKED = "revoked", "Revocada"

    customer = models.ForeignKey(
        "customers.Customer", on_delete=models.PROTECT, related_name="client_invitations"
    )
    user = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.PROTECT, related_name="client_invitations"
    )
    email = models.EmailField(db_index=True)
    token_digest = models.CharField(max_length=64, unique=True, editable=False)
    kind = models.CharField(max_length=30, choices=Kind.choices)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True)
    expires_at = models.DateTimeField(db_index=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    invited_by = models.ForeignKey(
        User, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_client_invitations"
    )

    class Meta:
        ordering = ["-created_at", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["customer"],
                condition=models.Q(status="pending"),
                name="unique_pending_client_invitation",
            )
        ]
        indexes = [models.Index(fields=["email", "status"])]
        verbose_name = "Invitación de cliente"
        verbose_name_plural = "Invitaciones de clientes"

    @property
    def is_expired(self):
        return self.expires_at <= timezone.now()

    def __str__(self):
        return f"{self.email} · {self.get_status_display()}"
