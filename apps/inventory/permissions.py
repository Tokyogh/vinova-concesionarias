"""ES: Este módulo centraliza reglas de autorización para el dominio de inventario.

EN: This module centralizes authorization rules for the inventory domain.

Contexto existente / Existing context:
Authorization helpers for the inventory domain.
"""

def can_view_inventory(user):
    return user.is_authenticated and (user.has_perm_code("inventory.view") or user.has_perm_code("inventory.manage_stock"))


def can_manage_inventory(user):
    return user.is_authenticated and user.has_perm_code("inventory.manage_stock")
