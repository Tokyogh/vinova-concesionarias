"""ES: Este módulo registra modelos en la administración de Django para el dominio de empresa.

EN: This module registers models in Django admin for the companies domain.

Contexto existente / Existing context:
Django admin registrations for the companies domain.
"""

from django.contrib import admin
from apps.companies.models import Company


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ["commercial_name", "ruc", "email", "is_active"]
    search_fields = ["commercial_name", "legal_name", "ruc"]
