"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de sucursales.

EN: This module orchestrates HTTP requests, permissions, and responses for the branches domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the branches domain.
"""

from rest_framework import viewsets
from rest_framework.permissions import BasePermission

from apps.accounts.scopes import has_global_permission
from apps.branches.api.serializers import BranchSerializer
from apps.branches.selectors import branch_list_queryset
from apps.branches.services import create_branch, update_branch


class GlobalBranchPermission(BasePermission):
    def has_permission(self, request, view):
        return has_global_permission(request.user, "branches.manage")


class BranchViewSet(viewsets.ModelViewSet):
    serializer_class = BranchSerializer
    permission_classes = [GlobalBranchPermission]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    search_fields = ["name", "code", "city", "company__commercial_name"]
    filterset_fields = ["branch_type", "is_active", "is_public", "company"]
    ordering_fields = ["city", "name", "created_at"]

    def get_queryset(self):
        return branch_list_queryset(query="")

    def perform_create(self, serializer):
        create_branch(actor=self.request.user, form=serializer)

    def perform_update(self, serializer):
        update_branch(actor=self.request.user, branch=serializer.instance, form=serializer)
