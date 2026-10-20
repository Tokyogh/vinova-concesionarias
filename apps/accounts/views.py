"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de cuentas.

EN: This module orchestrates HTTP requests, permissions, and responses for the accounts domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the accounts domain.
"""

from __future__ import annotations

import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.views import (
    LoginView,
    LogoutView,
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import CreateView, DetailView, FormView, ListView, TemplateView, UpdateView

from apps.accounts.client_services import (
    accept_client_invitation,
    create_client_registration,
    get_client_invitation,
    send_client_access_email,
)
from apps.accounts.forms import (
    AdminPasswordSetForm,
    AvatarUploadForm,
    ClientActivationConfirmForm,
    ClientInvitationAcceptForm,
    ClientRegistrationForm,
    InternalUserCreateForm,
    InternalUserUpdateForm,
    UserRoleAssignForm,
    UserSearchForm,
    VinovaPasswordResetForm,
    VinovaSetPasswordForm,
    VinovaLoginForm,
)
from apps.accounts.models import ClientInvitation, User, UserRole
from apps.accounts.selectors import (
    active_user_roles_for,
    manageable_users_queryset,
    user_detail_queryset,
    user_list_queryset,
    visible_user_roles_for,
)
from apps.accounts.services import (
    assign_role_to_user,
    create_internal_user,
    remove_user_role,
    set_user_password_by_admin,
    toggle_user_active_state,
    update_internal_user,
)
from apps.accounts.storage import resolved_avatar_provider
from apps.common.http import safe_next_url
from apps.common.rate_limit import public_rate_limit_exceeded, public_rate_limited_response
from apps.customers.models import Customer
from apps.enterprise.selectors import get_primary_company, get_public_settings

logger = logging.getLogger(__name__)


def _delete_avatar_file(storage, name: str, *, context: str) -> None:
    if not name:
        return
    try:
        storage.delete(name)
    except Exception as exc:  # noqa: BLE001 - cleanup is best effort
        logger.warning("No se pudo limpiar el avatar %s (%s).", context, exc.__class__.__name__)


def _profile_route_for(user):
    if (
        user.has_perm_code("portal.access")
        and Customer.objects.filter(
            account=user,
            is_deleted=False,
        ).exists()
    ):
        return "portal:profile"
    return "accounts:profile"


class VinovaLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = VinovaLoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        self.request.session["vinova_2fa_verified"] = False
        return response

    def get_success_url(self):
        user = self.request.user
        if getattr(user, "can_access_internal_panel", False):
            return reverse("dashboard:staff_home")
        if user.has_perm_code("portal.access"):
            return reverse("portal:dashboard")
        return reverse("accounts:profile")

    def form_invalid(self, form):
        messages.error(self.request, "No se pudo iniciar sesión. Revisa el usuario/correo y contraseña.")
        return super().form_invalid(form)


class VinovaLogoutView(LogoutView):
    next_page = reverse_lazy("accounts:login")


def _client_registration_enabled() -> bool:
    company = get_primary_company()
    if company is None:
        return False
    return bool(get_public_settings(company).allow_client_registration)


class ClientRegistrationView(FormView):
    template_name = "accounts/client_registration.html"
    form_class = ClientRegistrationForm
    success_url = reverse_lazy("accounts:client_registration_done")

    def dispatch(self, request, *args, **kwargs):
        if not _client_registration_enabled():
            raise Http404("El registro público de clientes no está habilitado.")
        return super().dispatch(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        if public_rate_limit_exceeded(request, scope="client-registration"):
            return public_rate_limited_response()
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        try:
            invitation, raw_token = create_client_registration(cleaned_data=form.cleaned_data)
        except ValidationError as exc:
            form.add_error(None, exc.message if hasattr(exc, "message") else str(exc))
            return self.form_invalid(form)
        accept_url = self.request.build_absolute_uri(
            reverse("accounts:client_invitation_accept", kwargs={"token": raw_token})
        )
        send_client_access_email(invitation=invitation, raw_token=raw_token, accept_url=accept_url)
        return super().form_valid(form)


class ClientRegistrationDoneView(TemplateView):
    template_name = "accounts/client_registration_done.html"


class ClientInvitationAcceptView(View):
    template_name = "accounts/client_invitation_accept.html"
    invalid_template_name = "accounts/client_invitation_invalid.html"

    def dispatch(self, request, *args, **kwargs):
        self.raw_token = kwargs["token"]
        try:
            self.invitation = get_client_invitation(self.raw_token)
        except ValidationError as exc:
            return render(
                request,
                self.invalid_template_name,
                {"error": exc.message if hasattr(exc, "message") else str(exc)},
                status=410,
            )
        return super().dispatch(request, *args, **kwargs)

    def _form(self, data=None):
        if self.invitation.kind == ClientInvitation.Kind.STAFF_INVITATION:
            return ClientInvitationAcceptForm(data, email=self.invitation.email)
        return ClientActivationConfirmForm(data)

    def get(self, request, *args, **kwargs):
        return render(request, self.template_name, {"invitation": self.invitation, "form": self._form()})

    def post(self, request, *args, **kwargs):
        if public_rate_limit_exceeded(request, scope="client-invitation-accept"):
            return public_rate_limited_response()
        form = self._form(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"invitation": self.invitation, "form": form})
        try:
            accept_client_invitation(
                raw_token=self.raw_token,
                password=form.cleaned_data.get("password1"),
            )
        except ValidationError as exc:
            form.add_error(None, exc.message if hasattr(exc, "message") else str(exc))
            return render(request, self.template_name, {"invitation": self.invitation, "form": form})
        messages.success(request, "Tu cuenta quedó activa. Ya puedes iniciar sesión.")
        return redirect("accounts:login")


class VinovaPasswordResetView(PasswordResetView):
    template_name = "accounts/password_reset_form.html"
    email_template_name = "accounts/email/password_reset_email.txt"
    subject_template_name = "accounts/email/password_reset_subject.txt"
    form_class = VinovaPasswordResetForm
    success_url = reverse_lazy("accounts:password_reset_done")

    def post(self, request, *args, **kwargs):
        if public_rate_limit_exceeded(request, scope="password-reset"):
            return public_rate_limited_response()
        return super().post(request, *args, **kwargs)


class VinovaPasswordResetDoneView(PasswordResetDoneView):
    template_name = "accounts/password_reset_done.html"


class VinovaPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = "accounts/password_reset_confirm.html"
    form_class = VinovaSetPasswordForm
    success_url = reverse_lazy("accounts:password_reset_complete")

    def form_valid(self, form):
        response = super().form_valid(form)
        from apps.security_center.services import revoke_user_sessions

        revoke_user_sessions(
            user=form.user,
            actor=form.user,
            reason="Contraseña restablecida",
        )
        return response


class VinovaPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = "accounts/password_reset_complete.html"


class UserProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and _profile_route_for(request.user) == "portal:profile":
            return redirect("portal:profile")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["active_roles"] = active_user_roles_for(self.request.user)
        ctx["avatar_form"] = AvatarUploadForm()
        return ctx


class AvatarUpdateView(LoginRequiredMixin, View):
    """Subida, sustitución y edición del avatar del propio usuario."""

    def post(self, request):
        form = AvatarUploadForm(request.POST, request.FILES)
        if not form.is_valid():
            errors = " ".join(error for field_errors in form.errors.values() for error in field_errors)
            messages.error(request, f"No se pudo actualizar la fotografía. {errors}".strip())
            return redirect(_profile_route_for(request.user))

        user = request.user
        old_name = user.avatar.name if user.avatar else None
        old_storage = user.avatar.storage if user.avatar else None

        try:
            user.avatar = form.cleaned_data["avatar"]
            user.avatar_provider = resolved_avatar_provider()
            with transaction.atomic():
                user.save(update_fields=["avatar", "avatar_provider"])
        except Exception as exc:  # noqa: BLE001 - proveedor externo no debe romper la vista
            failed_name = user.avatar.name if user.avatar else None
            failed_storage = user.avatar.storage if user.avatar else None
            if failed_storage and failed_name and failed_name != old_name:
                _delete_avatar_file(failed_storage, failed_name, context="nuevo")
            logger.warning("Falló la actualización del avatar (%s).", exc.__class__.__name__)
            user.refresh_from_db(fields=["avatar", "avatar_provider"])
            messages.error(request, "No se pudo guardar la fotografía. Inténtalo nuevamente más tarde.")
            return redirect(_profile_route_for(request.user))

        if old_name and old_name != user.avatar.name:
            transaction.on_commit(lambda: _delete_avatar_file(old_storage, old_name, context="anterior"))

        messages.success(request, "Fotografía de perfil actualizada.")
        return redirect(_profile_route_for(request.user))


class AvatarDeleteView(LoginRequiredMixin, View):
    def post(self, request):
        user = request.user
        if not user.avatar:
            messages.info(request, "No tienes una fotografía de perfil registrada.")
            return redirect(_profile_route_for(request.user))

        old_name = user.avatar.name
        old_storage = user.avatar.storage
        try:
            with transaction.atomic():
                user.avatar = ""
                user.avatar_provider = user.AvatarProvider.LOCAL
                user.save(update_fields=["avatar", "avatar_provider"])
        except Exception as exc:  # noqa: BLE001 - proveedor externo no debe romper la vista
            logger.warning("Falló la eliminación del avatar (%s).", exc.__class__.__name__)
            user.refresh_from_db(fields=["avatar", "avatar_provider"])
            messages.error(request, "No se pudo eliminar la fotografía. Inténtalo nuevamente más tarde.")
            return redirect(_profile_route_for(request.user))
        transaction.on_commit(lambda: _delete_avatar_file(old_storage, old_name, context="eliminado"))
        messages.success(request, "Fotografía de perfil eliminada.")
        return redirect(_profile_route_for(request.user))


class PermissionCodeRequiredMixin(LoginRequiredMixin):
    permission_code: str | None = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if self.permission_code and not request.user.has_perm_code(self.permission_code):
            raise PermissionDenied("No tienes permisos para acceder a este módulo.")
        return super().dispatch(request, *args, **kwargs)


class UserListView(PermissionCodeRequiredMixin, ListView):
    permission_code = "accounts.manage_users"
    template_name = "accounts/user_list.html"
    context_object_name = "users"
    paginate_by = 20

    def get_queryset(self):
        self.search_form = UserSearchForm(self.request.GET)
        query = ""
        if self.search_form.is_valid():
            query = self.search_form.cleaned_data.get("q", "")
        return user_list_queryset(self.request.user, query=query)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_form"] = self.search_form
        ctx["query"] = self.request.GET.get("q", "")
        ctx["total_users"] = self.object_list.count()
        return ctx


class UserCreateView(PermissionCodeRequiredMixin, CreateView):
    permission_code = "accounts.manage_users"
    template_name = "accounts/user_form.html"
    form_class = InternalUserCreateForm
    model = User

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        self.object = create_internal_user(actor=self.request.user, form=form)
        messages.success(self.request, "Usuario creado correctamente.")
        return redirect("accounts:user_detail", pk=self.object.pk)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["mode"] = "create"
        ctx["page_heading"] = "Crear usuario interno"
        return ctx


class UserDetailView(PermissionCodeRequiredMixin, DetailView):
    permission_code = "accounts.manage_users"
    template_name = "accounts/user_detail.html"
    context_object_name = "managed_user"

    def get_queryset(self):
        return user_detail_queryset(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["role_form"] = UserRoleAssignForm(user=self.request.user)
        ctx["password_form"] = AdminPasswordSetForm(user=self.object)
        ctx["active_roles"] = visible_user_roles_for(self.request.user, self.object)
        return ctx


class UserUpdateView(PermissionCodeRequiredMixin, UpdateView):
    permission_code = "accounts.manage_users"
    template_name = "accounts/user_form.html"
    form_class = InternalUserUpdateForm
    context_object_name = "managed_user"

    def get_queryset(self):
        return user_detail_queryset(self.request.user)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        self.object = update_internal_user(actor=self.request.user, user=self.object, form=form)
        messages.success(self.request, "Usuario actualizado correctamente.")
        return redirect("accounts:user_detail", pk=self.object.pk)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["mode"] = "update"
        ctx["page_heading"] = "Editar usuario"
        return ctx


class UserAssignRoleView(PermissionCodeRequiredMixin, View):
    permission_code = "accounts.assign_roles"

    def post(self, request, pk):
        user = get_object_or_404(manageable_users_queryset(request.user, active_only=False), pk=pk)
        form = UserRoleAssignForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                assign_role_to_user(
                    actor=request.user,
                    user=user,
                    role=form.cleaned_data["role"],
                    branch=form.cleaned_data.get("branch"),
                    starts_at=form.cleaned_data.get("starts_at"),
                    expires_at=form.cleaned_data.get("expires_at"),
                )
            except (PermissionDenied, ValueError) as exc:
                messages.error(request, str(exc))
                return redirect("accounts:user_detail", pk=user.pk)
            messages.success(request, "Rol asignado correctamente.")
        else:
            errors = []
            for field, field_errors in form.errors.items():
                label = form.fields[field].label if field in form.fields else "Formulario"
                for error in field_errors:
                    errors.append(f"{label}: {error}")
            messages.error(request, "No se pudo asignar el rol. " + " ".join(errors))
        return redirect("accounts:user_detail", pk=user.pk)


class UserRemoveRoleView(PermissionCodeRequiredMixin, View):
    permission_code = "accounts.assign_roles"

    def post(self, request, pk, user_role_pk):
        user_role = get_object_or_404(
            UserRole.objects.select_related("user", "role", "branch"),
            pk=user_role_pk,
            user_id=pk,
            user__in=manageable_users_queryset(request.user, active_only=False),
        )
        try:
            remove_user_role(actor=request.user, user_role=user_role)
            messages.success(request, "Rol retirado correctamente.")
        except PermissionDenied as exc:
            messages.error(request, str(exc))
        return redirect("accounts:user_detail", pk=pk)


class UserToggleActiveView(PermissionCodeRequiredMixin, View):
    permission_code = "accounts.manage_users"

    def post(self, request, pk):
        user = get_object_or_404(manageable_users_queryset(request.user, active_only=False), pk=pk)
        if user.pk == request.user.pk:
            messages.error(request, "No puedes desactivar tu propio usuario desde esta acción.")
            return redirect("accounts:user_detail", pk=user.pk)
        toggle_user_active_state(actor=request.user, user=user)
        state = "activado" if user.is_active else "desactivado"
        messages.success(request, f"Usuario {state} correctamente.")
        fallback = reverse("accounts:user_detail", kwargs={"pk": user.pk})
        return redirect(safe_next_url(request, request.POST.get("next"), fallback))


class UserAdminPasswordView(PermissionCodeRequiredMixin, View):
    permission_code = "accounts.manage_users"

    def post(self, request, pk):
        user = get_object_or_404(manageable_users_queryset(request.user, active_only=False), pk=pk)
        form = AdminPasswordSetForm(request.POST, user=user)
        if form.is_valid():
            set_user_password_by_admin(
                actor=request.user,
                user=user,
                password=form.cleaned_data["password2"],
                must_change_password=form.cleaned_data.get("must_change_password", True),
            )
            messages.success(request, "Contraseña actualizada correctamente.")
        else:
            messages.error(request, "No se pudo cambiar la contraseña. Revisa la seguridad y coincidencia.")
        return redirect("accounts:user_detail", pk=user.pk)
