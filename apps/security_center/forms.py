"""ES: Este módulo define formularios y validación de entrada en backend para el dominio de seguridad.

EN: This module defines forms and server-side input validation for the security center domain.

Contexto existente / Existing context:
Server-side forms and input validation for the security center domain.
"""

from django import forms
from django.contrib.auth import password_validation

from apps.security_center.models import SecurityPolicy
from apps.security_center.staff_access import parse_trusted_staff_networks


class TwoFactorChallengeForm(forms.Form):
    token = forms.CharField(label="Código de 6 dígitos o código de recuperación", max_length=32, widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "one-time-code", "inputmode": "numeric"}))


class TwoFactorSetupForm(forms.Form):
    current_password = forms.CharField(label="Contraseña actual", strip=False, widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "current-password"}))
    token = forms.CharField(label="Código generado por la aplicación", max_length=12, widget=forms.TextInput(attrs={"class": "form-control", "autocomplete": "one-time-code", "inputmode": "numeric"}))

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        value = self.cleaned_data["current_password"]
        if not self.user or not self.user.check_password(value):
            raise forms.ValidationError("La contraseña actual no es correcta.")
        return value


class TwoFactorDisableForm(forms.Form):
    current_password = forms.CharField(label="Contraseña actual", strip=False, widget=forms.PasswordInput(attrs={"class": "form-control"}))
    token = forms.CharField(label="Código 2FA", max_length=32, widget=forms.TextInput(attrs={"class": "form-control"}))

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_current_password(self):
        value = self.cleaned_data["current_password"]
        if not self.user or not self.user.check_password(value):
            raise forms.ValidationError("La contraseña actual no es correcta.")
        return value


class SecurePasswordChangeForm(forms.Form):
    old_password = forms.CharField(label="Contraseña actual", strip=False, widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "current-password"}))
    new_password1 = forms.CharField(label="Nueva contraseña", strip=False, widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}))
    new_password2 = forms.CharField(label="Confirmar nueva contraseña", strip=False, widget=forms.PasswordInput(attrs={"class": "form-control", "autocomplete": "new-password"}))

    def __init__(self, *args, user=None, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)

    def clean_old_password(self):
        value = self.cleaned_data["old_password"]
        if not self.user.check_password(value):
            raise forms.ValidationError("La contraseña actual no es correcta.")
        return value

    def clean_new_password2(self):
        p1 = self.cleaned_data.get("new_password1")
        p2 = self.cleaned_data.get("new_password2")
        if p1 and p2 and p1 != p2:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        if p2:
            password_validation.validate_password(p2, self.user)
        return p2


class SecurityPolicyForm(forms.ModelForm):
    class Meta:
        model = SecurityPolicy
        fields = [
            "min_password_length", "require_uppercase", "require_lowercase", "require_digit", "require_symbol",
            "password_max_age_days", "password_history_count", "session_idle_minutes", "max_active_sessions",
            "login_attempts_per_ip", "login_window_minutes", "require_2fa_for_superusers",
            "require_2fa_for_admin_roles", "admin_role_level_threshold",
            "staff_access_mode", "trusted_staff_networks", "staff_access_approval_minutes",
            "staff_access_request_minutes",
        ]
        labels = {
            "min_password_length": "Longitud mínima",
            "password_max_age_days": "Vencimiento de contraseña (días)",
            "password_history_count": "Contraseñas anteriores bloqueadas",
            "session_idle_minutes": "Cierre por inactividad (minutos)",
            "max_active_sessions": "Sesiones simultáneas máximas",
            "login_attempts_per_ip": "Intentos máximos por ventana/IP",
            "login_window_minutes": "Ventana de intentos (minutos)",
            "require_2fa_for_superusers": "Exigir 2FA a superusuarios",
            "require_2fa_for_admin_roles": "Exigir 2FA a roles administrativos",
            "admin_role_level_threshold": "Nivel máximo considerado administrativo",
            "staff_access_mode": "Acceso Staff según riesgo",
            "trusted_staff_networks": "Redes corporativas o VPN confiables",
            "staff_access_approval_minutes": "Duración de aprobación excepcional (minutos)",
            "staff_access_request_minutes": "Vigencia de solicitud pendiente (minutos)",
        }
        help_texts = {
            "require_uppercase": "No se recomienda exigir composición salvo obligación empresarial documentada.",
            "require_lowercase": "No se recomienda exigir composición salvo obligación empresarial documentada.",
            "require_digit": "No se recomienda exigir composición salvo obligación empresarial documentada.",
            "require_symbol": "No se recomienda exigir composición salvo obligación empresarial documentada.",
            "password_max_age_days": "Usa 0 para no forzar cambios periódicos; cambia contraseñas ante compromiso.",
            "staff_access_mode": "Monitoreo solo audita; aplicar restricciones bloquea accesos fuera de política.",
            "trusted_staff_networks": "Una IP o CIDR por línea. No se recopila GPS.",
        }
        widgets = {field: forms.NumberInput(attrs={"class": "form-control"}) for field in ["min_password_length", "password_max_age_days", "password_history_count", "session_idle_minutes", "max_active_sessions", "login_attempts_per_ip", "login_window_minutes", "admin_role_level_threshold", "staff_access_approval_minutes", "staff_access_request_minutes"]}
        widgets["staff_access_mode"] = forms.Select(attrs={"class": "form-select"})
        widgets["trusted_staff_networks"] = forms.Textarea(attrs={"class": "form-control", "rows": 5})

    def clean_trusted_staff_networks(self):
        value = self.cleaned_data.get("trusted_staff_networks", "")
        parse_trusted_staff_networks(value)
        return value

    def clean_staff_access_approval_minutes(self):
        value = self.cleaned_data["staff_access_approval_minutes"]
        if not 5 <= value <= 1440:
            raise forms.ValidationError("La aprobación debe durar entre 5 minutos y 24 horas.")
        return value

    def clean_staff_access_request_minutes(self):
        value = self.cleaned_data["staff_access_request_minutes"]
        if not 5 <= value <= 60:
            raise forms.ValidationError("La solicitud debe durar entre 5 y 60 minutos.")
        return value


class StaffAccessDecisionForm(forms.Form):
    """ES: Nota acotada de decisión. EN: Bounded access-decision note."""

    note = forms.CharField(
        label="Observación",
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={"class": "form-control", "rows": 3}),
    )
