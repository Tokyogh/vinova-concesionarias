"""ES: Este módulo implementa el componente passwords para el dominio de seguridad.

EN: This module implements the passwords component for the security center domain.

Contexto existente / Existing context:
Passwords support for the security center domain.
"""

from __future__ import annotations

import re

from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from apps.security_center.models import PasswordHistory, SecurityPolicy


class VinovaPasswordPolicyValidator:
    """ES: Agrupa el componente «vinova password policy validator» del dominio de seguridad y sus reglas relacionadas. Además, rechaza estados o entradas inválidas.

    EN: Groups the «vinova password policy validator» component and its related rules in the security center domain. It also rejects invalid input or state.
    """

    def validate(self, password, user=None):
        """ES: Valida y normaliza «validate» antes de permitir efectos en seguridad. Además, rechaza estados o entradas inválidas.

        EN: Validates and normalizes «validate» before allowing effects in security center. It also rejects invalid input or state.
        """

        policy = SecurityPolicy.current()
        errors = []
        if len(password) < policy.min_password_length:
            errors.append(_(f"La contraseña debe tener al menos {policy.min_password_length} caracteres."))
        if policy.require_uppercase and not re.search(r"[A-ZÁÉÍÓÚÑ]", password):
            errors.append(_("La contraseña debe incluir una letra mayúscula."))
        if policy.require_lowercase and not re.search(r"[a-záéíóúñ]", password):
            errors.append(_("La contraseña debe incluir una letra minúscula."))
        if policy.require_digit and not re.search(r"\d", password):
            errors.append(_("La contraseña debe incluir un número."))
        if policy.require_symbol and not re.search(r"[^\w\s]", password, flags=re.UNICODE):
            errors.append(_("La contraseña debe incluir un símbolo."))
        if user and getattr(user, "pk", None) and policy.password_history_count:
            recent = PasswordHistory.objects.filter(user=user).order_by("-created_at")[: policy.password_history_count]
            if any(check_password(password, item.encoded_password) for item in recent):
                errors.append(_(f"No puedes reutilizar ninguna de tus últimas {policy.password_history_count} contraseñas."))
            if getattr(user, "password", "") and check_password(password, user.password):
                errors.append(_("La nueva contraseña no puede ser igual a la actual."))
        if errors:
            raise ValidationError(errors)

    def get_help_text(self):
        return _("Usa una frase de contraseña extensa, única y difícil de adivinar.")
