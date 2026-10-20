"""ES: Este módulo centraliza reglas de autorización para el dominio de ventas.

EN: This module centralizes authorization rules for the sales domain.

Contexto existente / Existing context:
Authorization helpers for the sales domain.
"""

def can_view_sales(user):
    return user.is_authenticated and (user.has_perm_code("sales.quote") or user.has_perm_code("sales.reserve") or user.has_perm_code("sales.sell"))


def can_manage_quotes(user):
    return user.is_authenticated and user.has_perm_code("sales.quote")


def can_manage_reservations(user):
    return user.is_authenticated and user.has_perm_code("sales.reserve")


def can_confirm_sales(user):
    return user.is_authenticated and user.has_perm_code("sales.sell")
