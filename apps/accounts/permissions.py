"""ES: Este módulo centraliza reglas de autorización para el dominio de cuentas.

EN: This module centralizes authorization rules for the accounts domain.

Contexto existente / Existing context:
Authorization helpers for the accounts domain.
"""

from django.core.exceptions import PermissionDenied
def require_perm_code(user, code, *, branch=None):
    if not user.is_authenticated or not user.has_perm_code(code, branch=branch):
        raise PermissionDenied(f'No tienes permiso para: {code}')
