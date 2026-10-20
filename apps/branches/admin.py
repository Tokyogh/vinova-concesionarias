"""ES: Este módulo registra modelos en la administración de Django para el dominio de sucursales.

EN: This module registers models in Django admin for the branches domain.

Contexto existente / Existing context:
Django admin registrations for the branches domain.
"""

from django.contrib import admin
from apps.branches.models import Branch


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ["name", "company", "city", "branch_type", "is_public", "is_active"]
    search_fields = ["name", "code", "city", "province", "address"]
    list_filter = ["branch_type", "city", "is_public", "is_active"]
