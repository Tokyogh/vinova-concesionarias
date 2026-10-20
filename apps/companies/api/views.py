"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de empresa.

EN: This module orchestrates HTTP requests, permissions, and responses for the companies domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the companies domain.
"""

from rest_framework import viewsets
from rest_framework.permissions import BasePermission

from apps.accounts.scopes import has_global_permission
from apps.companies.api.serializers import CompanySerializer
from apps.companies.selectors import company_list_queryset
from apps.companies.services import create_company, update_company


class GlobalCompanyPermission(BasePermission):
    def has_permission(self, request, view):
        return has_global_permission(request.user, "companies.manage")


class CompanyViewSet(viewsets.ModelViewSet):
    serializer_class = CompanySerializer
    permission_classes = [GlobalCompanyPermission]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    search_fields = ["commercial_name", "legal_name", "ruc"]
    ordering_fields = ["commercial_name", "created_at"]

    def get_queryset(self):
        return company_list_queryset(query="")

    def perform_create(self, serializer):
        create_company(actor=self.request.user, form=serializer)

    def perform_update(self, serializer):
        update_company(actor=self.request.user, company=serializer.instance, form=serializer)
