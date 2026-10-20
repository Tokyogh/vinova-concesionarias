"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de vehículos.

EN: This module orchestrates HTTP requests, permissions, and responses for the vehicles domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the vehicles domain.
"""

from rest_framework import viewsets
from rest_framework.permissions import BasePermission

from apps.vehicles.api.serializers import VehicleSerializer
from apps.vehicles.selectors import vehicle_detail_queryset


class VehicleApiPermission(BasePermission):
    def has_permission(self, request, view):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return any(
                user.has_perm_code(code)
                for code in ("vehicles.view", "vehicles.manage", "vehicles.publish")
            )
        return user.has_perm_code("vehicles.manage")


class VehicleViewSet(viewsets.ModelViewSet):
    serializer_class = VehicleSerializer
    permission_classes = [VehicleApiPermission]
    http_method_names = ["get", "post", "put", "patch", "head", "options"]
    search_fields = ["vin", "plate", "brand__name", "model__name", "version"]
    ordering_fields = ["year", "price", "created_at"]
    filterset_fields = ["status", "branch", "brand", "model", "year"]

    def get_queryset(self):
        permission_codes = (
            ("vehicles.manage",)
            if self.action in {"update", "partial_update"}
            else ("vehicles.view", "vehicles.manage", "vehicles.publish")
        )
        return vehicle_detail_queryset(self.request.user, permission_codes=permission_codes)
