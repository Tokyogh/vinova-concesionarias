"""ES: Este módulo define formularios y validación de entrada en backend para el dominio de cuentas.

EN: This module defines forms and server-side input validation for the accounts domain.

Contexto existente / Existing context:
Server-side forms and input validation for the accounts domain.
"""

from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, PasswordResetForm, SetPasswordForm, UserCreationForm
from django.contrib.auth.password_validation import validate_password

from apps.accounts.models import Role
from apps.accounts.scopes import accessible_branches_queryset, assignable_role_queryset_for
from apps.branches.models import Branch
from apps.common.form_widgets import make_searchable_select
from apps.common.validators import validate_avatar_image, validate_human_name, validate_phone_number

User = get_user_model()

# Roles where branch assignment is part of operational traceability.
# Normal users, clients, auditors and global admins can remain without a branch.
BRANCH_REQUIRED_ROLE_CODES = {
    "admin_sucursal",
    "jefe_inventario",
    "vendedor",
    "asesor_postventa",
    "facturacion",
    "bodega",
}


class VinovaLoginForm(AuthenticationForm):
    username = forms.CharField(
        label="Usuario o correo",
        widget=forms.TextInput(attrs={"class": "form-control", "placeholder": "usuario@empresa.com"}),
    )
    password = forms.CharField(
        label="Contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Tu contraseña"}),
    )

    error_messages = {
        "invalid_login": "Usuario/correo o contraseña incorrectos. Revisa tus datos o contacta al administrador.",
        "inactive": "Esta cuenta está desactivada.",
    }


class ClientRegistrationForm(forms.Form):
    first_name = forms.CharField(label="Nombres", max_length=100, validators=[validate_human_name], widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "given-name"}))
    last_name = forms.CharField(label="Apellidos", max_length=120, validators=[validate_human_name], widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "family-name"}))
    email = forms.EmailField(label="Correo", widget=forms.EmailInput(attrs={"class": "form-control", "autocomplete": "email"}))
    phone = forms.CharField(label="Teléfono", max_length=30, required=False, validators=[validate_phone_number], widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "tel", "inputmode": "tel"}))
    password1 = forms.CharField(label="Contraseña", strip=False, widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}))
    password2 = forms.CharField(label="Confirmar contraseña", strip=False, widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}))
    accept_terms = forms.BooleanField(label="Acepto los términos y condiciones del portal")
    privacy_acknowledgement = forms.BooleanField(
        label="Confirmo que leí el aviso de privacidad",
        help_text="Esta confirmación no autoriza marketing ni tecnologías opcionales.",
    )

    def clean_email(self):
        return self.cleaned_data["email"].strip().lower()

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Las contraseñas no coinciden.")
        if password1:
            candidate = User(
                email=cleaned.get("email", ""),
                first_name=cleaned.get("first_name", ""),
                last_name=cleaned.get("last_name", ""),
            )
            try:
                validate_password(password1, user=candidate)
            except forms.ValidationError as exc:
                self.add_error("password1", exc)
        return cleaned


class ClientInvitationAcceptForm(forms.Form):
    password1 = forms.CharField(label="Contraseña", strip=False, widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}))
    password2 = forms.CharField(label="Confirmar contraseña", strip=False, widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}))

    def __init__(self, *args, email="", **kwargs):
        self.email = email
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 and password2 and password1 != password2:
            self.add_error("password2", "Las contraseñas no coinciden.")
        if password1:
            try:
                validate_password(password1, user=User(email=self.email))
            except forms.ValidationError as exc:
                self.add_error("password1", exc)
        return cleaned


class ClientActivationConfirmForm(forms.Form):
    confirm = forms.BooleanField(label="Confirmo que deseo activar mi cuenta", required=True)


class VinovaPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        label="Correo",
        widget=forms.EmailInput(attrs={"class": "form-control", "autocomplete": "email"}),
    )


class VinovaSetPasswordForm(SetPasswordForm):
    new_password1 = forms.CharField(
        label="Nueva contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
    )
    new_password2 = forms.CharField(
        label="Confirmar contraseña",
        strip=False,
        widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}),
    )

    def save(self, commit=True):
        """ES: Usa el servicio auditable de contraseñas. EN: Uses the auditable password service."""

        password = self.cleaned_data["new_password1"]
        if not commit:
            self.user.set_password(password)
            return self.user
        from apps.security_center.services import set_password_securely

        return set_password_securely(
            actor=self.user,
            user=self.user,
            password=password,
            action="security.password.reset",
        )


class UserSearchForm(forms.Form):
    q = forms.CharField(
        required=False,
        label="Buscar",
        widget=forms.SearchInput(attrs={"placeholder": "Buscar por nombre, usuario, correo o teléfono", "class": "form-control"}),
    )


class AvatarUploadForm(forms.Form):
    avatar = forms.ImageField(
        label="Fotografía de perfil",
        validators=[validate_avatar_image],
        widget=forms.ClearableFileInput(
            attrs={"class": "form-control", "accept": "image/jpeg,image/png,image/webp"}
        ),
        help_text="JPG, PNG o WEBP. Se valida el contenido real, el tamaño y las dimensiones.",
    )


class InternalUserCreateForm(UserCreationForm):
    email = forms.EmailField(label="Correo", widget=forms.EmailInput(attrs={"class": "form-control"}))
    first_name = forms.CharField(label="Nombres", required=False, validators=[validate_human_name], widget=forms.TextInput(attrs={"class": "form-control"}))
    last_name = forms.CharField(label="Apellidos", required=False, validators=[validate_human_name], widget=forms.TextInput(attrs={"class": "form-control"}))
    phone = forms.CharField(label="Teléfono", required=False, validators=[validate_phone_number], widget=forms.TextInput(attrs={"class": "form-control", "inputmode": "tel"}))
    branch = forms.ModelChoiceField(
        label="Sucursal principal opcional",
        required=False,
        queryset=Branch.objects.filter(is_active=True).select_related("company"),
        widget=forms.Select(attrs={"class": "form-control"}),
        help_text="Puede quedar vacío. La trazabilidad operativa se controla al asignar roles por sucursal.",
    )
    is_active = forms.BooleanField(label="Usuario activo", required=False, initial=True)
    must_change_password = forms.BooleanField(label="Exigir cambio de contraseña al iniciar", required=False, initial=True)

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["branch"].queryset = accessible_branches_queryset(user, permission_codes=("accounts.manage_users",))
        make_searchable_select(self.fields["branch"], "Buscar sucursal principal...")

    class Meta(UserCreationForm.Meta):
        model = User
        fields = [
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "branch",
            "is_active",
            "must_change_password",
        ]
        labels = {"username": "Nombre de usuario"}
        widgets = {"username": forms.TextInput(attrs={"class": "form-control"})}


class InternalUserUpdateForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ["username", "email", "first_name", "last_name", "phone", "branch", "is_active", "must_change_password"]
        labels = {
            "username": "Nombre de usuario",
            "email": "Correo",
            "first_name": "Nombres",
            "last_name": "Apellidos",
            "phone": "Teléfono",
            "branch": "Sucursal principal opcional",
            "is_active": "Usuario activo",
            "must_change_password": "Exigir cambio de contraseña",
        }
        help_texts = {
            "branch": "Puede quedar vacío. Para ventas, facturas e inventario se recomienda asignar roles operativos con sucursal.",
        }
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
            "first_name": forms.TextInput(attrs={"class": "form-control"}),
            "last_name": forms.TextInput(attrs={"class": "form-control"}),
            "phone": forms.TextInput(attrs={"class": "form-control"}),
            "branch": forms.Select(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].validators.append(validate_human_name)
        self.fields["last_name"].validators.append(validate_human_name)
        self.fields["phone"].validators.append(validate_phone_number)
        self.fields["phone"].widget.attrs.setdefault("inputmode", "tel")
        if user is not None:
            self.fields["branch"].queryset = accessible_branches_queryset(user, permission_codes=("accounts.manage_users",))
        make_searchable_select(self.fields["branch"], "Buscar sucursal principal...")


class UserRoleAssignForm(forms.Form):
    role = forms.ModelChoiceField(
        label="Rol",
        queryset=Role.objects.filter(is_active=True).order_by("level", "name"),
        widget=forms.Select(attrs={"class": "form-control"}),
    )
    branch = forms.ModelChoiceField(
        label="Sucursal específica",
        required=False,
        queryset=Branch.objects.filter(is_active=True).select_related("company"),
        widget=forms.Select(attrs={"class": "form-control"}),
        help_text="Déjalo vacío solo para roles globales. Roles operativos requieren sucursal para trazabilidad.",
    )
    starts_at = forms.DateTimeField(
        label="Vigente desde",
        required=False,
        widget=forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
    )
    expires_at = forms.DateTimeField(
        label="Vigente hasta",
        required=False,
        widget=forms.DateTimeInput(attrs={"class": "form-control", "type": "datetime-local"}),
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if user is not None:
            self.fields["branch"].queryset = accessible_branches_queryset(user, permission_codes=("accounts.assign_roles",))
            self.fields["role"].queryset = assignable_role_queryset_for(user).order_by("level", "name")
        make_searchable_select(self.fields["role"], "Buscar rol...")
        make_searchable_select(self.fields["branch"], "Buscar sucursal para el rol...")

    def clean(self):
        cleaned = super().clean()
        role = cleaned.get("role")
        branch = cleaned.get("branch")
        starts_at = cleaned.get("starts_at")
        expires_at = cleaned.get("expires_at")

        if starts_at and expires_at and expires_at <= starts_at:
            raise forms.ValidationError("La fecha de finalización debe ser posterior al inicio.")

        if role and role.code in BRANCH_REQUIRED_ROLE_CODES and branch is None:
            raise forms.ValidationError(
                "Este rol es operativo y requiere una sucursal específica para registrar correctamente ventas, facturas, stock o atención."
            )
        return cleaned


class AdminPasswordSetForm(forms.Form):
    password1 = forms.CharField(label="Nueva contraseña", strip=False, widget=forms.PasswordInput(attrs={"class": "form-control"}))
    password2 = forms.CharField(label="Confirmar contraseña", strip=False, widget=forms.PasswordInput(attrs={"class": "form-control"}))
    must_change_password = forms.BooleanField(label="Exigir cambio al iniciar sesión", required=False, initial=True)

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        if password2:
            validate_password(password2, user=self.user)
        return password2
