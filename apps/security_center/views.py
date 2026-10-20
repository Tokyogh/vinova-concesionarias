"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de seguridad.

EN: This module orchestrates HTTP requests, permissions, and responses for the security center domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the security center domain.
"""

from __future__ import annotations

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from datetime import timedelta
from django.views import View
from django.views.generic import FormView, ListView, TemplateView, UpdateView

from apps.accounts.scopes import accessible_branch_ids
from apps.accounts.views import PermissionCodeRequiredMixin
from apps.audit.models import AuditLog, SecurityAlert
from apps.audit.selectors import scoped_alert_queryset, scoped_audit_queryset
from apps.audit.services import audit_log
from apps.security_center.forms import (
    SecurityPolicyForm,
    SecurePasswordChangeForm,
    StaffAccessDecisionForm,
    TwoFactorChallengeForm,
    TwoFactorDisableForm,
    TwoFactorSetupForm,
)
from apps.security_center.models import ActiveSession, SecurityPolicy, StaffAccessRequest
from apps.security_center.rate_limit import (
    clear_two_factor_failures,
    is_two_factor_blocked,
    register_two_factor_failure,
)
from apps.security_center.services import (
    disable_two_factor,
    enable_two_factor,
    get_security_profile,
    register_session,
    revoke_session,
    revoke_user_sessions,
    set_password_securely,
    verify_two_factor,
)
from apps.security_center.selectors import active_sessions_queryset, security_profiles_queryset, security_users_queryset
from apps.security_center.totp import generate_secret, provisioning_uri
from apps.security_center.staff_access import (
    cancel_staff_access,
    decide_staff_access,
    revoke_staff_access,
    validate_staff_enforcement_readiness,
)


class SecurityDashboardView(PermissionCodeRequiredMixin, TemplateView):
    permission_code = "security.view"
    template_name = "security_center/internal/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        policy = SecurityPolicy.current()
        required_filter = Q(pk__in=[])
        if policy.require_2fa_for_superusers:
            required_filter |= Q(user__is_superuser=True)
        if policy.require_2fa_for_admin_roles:
            required_filter |= Q(
                user__user_roles__is_active=True,
                user__user_roles__role__is_active=True,
                user__user_roles__role__level__lte=policy.admin_role_level_threshold,
            )
        profiles = security_profiles_queryset(user=self.request.user)
        sessions = active_sessions_queryset(user=self.request.user)
        admin_without_2fa = profiles.filter(two_factor_enabled=False).filter(required_filter).distinct().count()
        audit_logs = scoped_audit_queryset(self.request.user, permission_code="security.view")
        alerts = scoped_alert_queryset(self.request.user, permission_code="security.view")
        ctx.update(
            {
                "policy": policy,
                "two_factor_total": profiles.filter(two_factor_enabled=True).count(),
                "admin_without_2fa": admin_without_2fa,
                "active_sessions": sessions.filter(revoked_at__isnull=True).count(),
                "failed_logins_24h": audit_logs.filter(
                    action="login.failed", occurred_at__gte=timezone.now() - timedelta(hours=24)
                ).count(),
                "open_alerts": alerts.filter(
                    status__in=[SecurityAlert.Status.OPEN, SecurityAlert.Status.IN_REVIEW]
                ).count(),
                "recent_sessions": sessions.order_by("-last_seen_at")[:12],
            }
        )
        return ctx


class SecurityPolicyUpdateView(PermissionCodeRequiredMixin, UpdateView):
    permission_code = "security.manage"
    form_class = SecurityPolicyForm
    template_name = "security_center/internal/policy_form.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and accessible_branch_ids(request.user, permission_codes=(self.permission_code,)) is not None:
            raise PermissionDenied("La política global requiere un permiso sin restricción de sucursal.")
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return SecurityPolicy.current()

    def form_valid(self, form):
        candidate = form.save(commit=False)
        if candidate.staff_access_mode == SecurityPolicy.StaffAccessMode.ENFORCE:
            try:
                validate_staff_enforcement_readiness(actor=self.request.user, policy=candidate)
            except ValidationError as exc:
                form.add_error(None, exc)
                return self.form_invalid(form)
        persisted = SecurityPolicy.objects.get(pk=self.object.pk)
        before = {field: getattr(persisted, field) for field in form.fields}
        response = super().form_valid(form)
        audit_log(
            user=self.request.user,
            action="security.policy.updated",
            target=self.object,
            before=before,
            after={field: getattr(self.object, field) for field in form.fields},
        )
        messages.success(self.request, "Política de seguridad actualizada.")
        return response

    def get_success_url(self):
        return reverse("security_center:dashboard")


class StaffAccessPendingView(LoginRequiredMixin, TemplateView):
    template_name = "security_center/account/staff_access_pending.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        request_id = self.request.session.get("vinova_staff_access_request_id")
        access_request = StaffAccessRequest.objects.filter(pk=request_id, user=self.request.user).first()
        ctx["access_request"] = access_request
        return ctx


class CancelStaffAccessView(LoginRequiredMixin, View):
    def post(self, request):
        request_id = request.session.get("vinova_staff_access_request_id")
        if not request_id:
            messages.info(request, "No existe una solicitud pendiente en esta sesión.")
            return redirect("security_center:staff_access_pending")
        try:
            cancel_staff_access(access_request_id=request_id, actor=request.user)
        except (StaffAccessRequest.DoesNotExist, ValidationError) as exc:
            messages.error(request, str(exc))
        else:
            request.session.pop("vinova_staff_access_request_id", None)
            messages.success(request, "Solicitud cancelada.")
        return redirect("accounts:profile")


class StaffAccessRequestListView(PermissionCodeRequiredMixin, ListView):
    permission_code = "security.approve_staff_access"
    template_name = "security_center/internal/staff_access_list.html"
    context_object_name = "access_requests"
    paginate_by = 50

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            if accessible_branch_ids(request.user, permission_codes=(self.permission_code,)) is not None:
                raise PermissionDenied("Las aprobaciones Staff requieren alcance global.")
            if not request.session.get("vinova_2fa_verified"):
                raise PermissionDenied("Verifica 2FA antes de revisar solicitudes Staff.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return StaffAccessRequest.objects.select_related("user", "decided_by").order_by("-created_at")


class StaffAccessDecisionView(PermissionCodeRequiredMixin, View):
    permission_code = "security.approve_staff_access"
    approve = False

    def post(self, request, pk):
        form = StaffAccessDecisionForm(request.POST)
        if not form.is_valid():
            messages.error(request, "La observación supera el límite permitido.")
            return redirect("security_center:staff_access_requests")
        try:
            decide_staff_access(
                access_request_id=pk,
                actor=request.user,
                approve=self.approve,
                note=form.cleaned_data["note"],
                actor_2fa_verified=bool(request.session.get("vinova_2fa_verified")),
            )
        except (PermissionDenied, ValidationError, StaffAccessRequest.DoesNotExist) as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "Solicitud aprobada temporalmente." if self.approve else "Solicitud rechazada.")
        return redirect("security_center:staff_access_requests")


class ApproveStaffAccessView(StaffAccessDecisionView):
    approve = True


class RejectStaffAccessView(StaffAccessDecisionView):
    approve = False


class RevokeStaffAccessView(PermissionCodeRequiredMixin, View):
    permission_code = "security.approve_staff_access"

    def post(self, request, pk):
        try:
            revoke_staff_access(
                access_request_id=pk,
                actor=request.user,
                actor_2fa_verified=bool(request.session.get("vinova_2fa_verified")),
            )
        except (PermissionDenied, ValidationError, StaffAccessRequest.DoesNotExist) as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, "Aprobación excepcional revocada.")
        return redirect("security_center:staff_access_requests")


class TwoFactorSetupView(LoginRequiredMixin, FormView):
    template_name = "security_center/account/two_factor_setup.html"
    form_class = TwoFactorSetupForm

    def dispatch(self, request, *args, **kwargs):
        if not request.session.get("vinova_2fa_setup_secret"):
            request.session["vinova_2fa_setup_secret"] = generate_secret()
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        secret = self.request.session["vinova_2fa_setup_secret"]
        ctx["secret"] = secret
        ctx["provisioning_uri"] = provisioning_uri(
            secret, account=self.request.user.email or self.request.user.username
        )
        ctx["profile"] = get_security_profile(self.request.user)
        return ctx

    def form_valid(self, form):
        secret = self.request.session["vinova_2fa_setup_secret"]
        try:
            codes = enable_two_factor(user=self.request.user, secret=secret, token=form.cleaned_data["token"])
        except ValueError as exc:
            form.add_error("token", str(exc))
            return self.form_invalid(form)
        self.request.session.pop("vinova_2fa_setup_secret", None)
        self.request.session["vinova_2fa_verified"] = True
        self.request.session["vinova_backup_codes_once"] = codes
        return redirect("security_center:backup_codes")


class BackupCodesView(LoginRequiredMixin, TemplateView):
    template_name = "security_center/account/backup_codes.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.session.get("vinova_backup_codes_once"):
            return redirect("accounts:profile")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["backup_codes"] = self.request.session.pop("vinova_backup_codes_once", [])
        return ctx


class TwoFactorChallengeView(LoginRequiredMixin, FormView):
    template_name = "security_center/account/two_factor_challenge.html"
    form_class = TwoFactorChallengeForm

    def form_valid(self, form):
        if is_two_factor_blocked(self.request, self.request.user):
            audit_log(
                user=self.request.user,
                action="security.2fa.rate_limited",
                target=self.request.user,
                result=AuditLog.Result.DENIED,
            )
            form.add_error("token", "Demasiados intentos. Espera antes de volver a intentar.")
            response = self.form_invalid(form)
            response.status_code = 429
            response["Retry-After"] = str(max(60, SecurityPolicy.current().login_window_minutes * 60))
            return response
        if not verify_two_factor(user=self.request.user, token=form.cleaned_data["token"]):
            register_two_factor_failure(self.request, self.request.user)
            audit_log(
                user=self.request.user,
                action="security.2fa.failed",
                target=self.request.user,
                result=AuditLog.Result.FAILED,
            )
            form.add_error("token", "Código incorrecto o vencido.")
            return self.form_invalid(form)
        clear_two_factor_failures(self.request, self.request.user)
        self.request.session["vinova_2fa_verified"] = True
        tracked = ActiveSession.objects.filter(session_key=self.request.session.session_key).first()
        if tracked:
            tracked.two_factor_verified_at = timezone.now()
            tracked.save(update_fields=["two_factor_verified_at", "updated_at"])
        audit_log(user=self.request.user, action="security.2fa.verified", target=self.request.user)
        return redirect(self.request.session.pop("vinova_2fa_next", None) or "dashboard:staff_home")


class TwoFactorDisableView(LoginRequiredMixin, FormView):
    template_name = "security_center/account/two_factor_disable.html"
    form_class = TwoFactorDisableForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        profile = get_security_profile(self.request.user)
        if profile.is_two_factor_required():
            form.add_error(None, "La política empresarial exige 2FA para esta cuenta.")
            return self.form_invalid(form)
        if not verify_two_factor(user=self.request.user, token=form.cleaned_data["token"]):
            form.add_error("token", "Código incorrecto.")
            return self.form_invalid(form)
        disable_two_factor(actor=self.request.user, user=self.request.user, reason="Desactivado por el usuario")
        self.request.session.pop("vinova_2fa_verified", None)
        messages.success(self.request, "Autenticación en dos pasos desactivada.")
        return redirect("accounts:profile")


class SecurePasswordChangeView(LoginRequiredMixin, FormView):
    template_name = "security_center/account/password_change.html"
    form_class = SecurePasswordChangeForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        old_session_key = self.request.session.session_key
        set_password_securely(
            actor=self.request.user, user=self.request.user, password=form.cleaned_data["new_password2"]
        )
        update_session_auth_hash(self.request, self.request.user)
        if old_session_key == self.request.session.session_key:
            self.request.session.cycle_key()
        revoke_user_sessions(
            user=self.request.user,
            actor=self.request.user,
            reason="Contraseña actualizada",
        )
        register_session(request=self.request, user=self.request.user)
        messages.success(self.request, "Contraseña actualizada correctamente.")
        return redirect("accounts:profile")


class MySessionsView(LoginRequiredMixin, TemplateView):
    template_name = "security_center/account/sessions.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["sessions"] = ActiveSession.objects.filter(user=self.request.user).order_by("-last_seen_at")
        ctx["current_session_key"] = self.request.session.session_key
        return ctx


class RevokeSessionView(LoginRequiredMixin, View):
    def post(self, request, pk):
        session = get_object_or_404(ActiveSession, pk=pk, user=request.user)
        if session.session_key == request.session.session_key:
            messages.error(request, "Usa el botón Salir para cerrar la sesión actual.")
        else:
            revoke_session(session, actor=request.user, reason="Revocada por el titular")
            messages.success(request, "Sesión revocada.")
        return redirect("security_center:my_sessions")


class AdminResetTwoFactorView(PermissionCodeRequiredMixin, View):
    permission_code = "security.manage"

    def post(self, request, pk):
        user = get_object_or_404(security_users_queryset(user=request.user, permission_code=self.permission_code), pk=pk)
        if user == request.user:
            messages.error(request, "No puedes restablecer tu propio 2FA desde administración.")
        else:
            disable_two_factor(actor=request.user, user=user, reason="Restablecido por administración")
            for session in ActiveSession.objects.filter(user=user, revoked_at__isnull=True):
                revoke_session(session, actor=request.user, reason="2FA restablecido por administración")
            messages.success(request, "2FA restablecido y sesiones cerradas.")
        return redirect("accounts:user_detail", pk=user.pk)
