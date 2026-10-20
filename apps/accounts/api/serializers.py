"""ES: Este módulo serializa y valida contratos de API para el dominio de cuentas.

EN: This module serializes and validates API contracts for the accounts domain.

Contexto existente / Existing context:
REST serializers and API validation for the accounts domain.
"""

from __future__ import annotations

from rest_framework import serializers

from apps.accounts.models import Role, User, UserRole
from apps.common.validators import validate_human_name, validate_phone_number

ACTIVE_API_ROLES_ATTR = "_active_api_roles"


class RoleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Role
        fields = ["id", "code", "name", "description", "level", "is_active"]


class UserRoleSerializer(serializers.ModelSerializer):
    role = RoleSerializer(read_only=True)

    class Meta:
        model = UserRole
        fields = ["id", "role", "branch", "is_active", "starts_at", "expires_at"]


class UserSerializer(serializers.ModelSerializer):
    roles = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "phone",
            "branch",
            "is_active",
            "roles",
        ]
        extra_kwargs = {
            "first_name": {"validators": [validate_human_name]},
            "last_name": {"validators": [validate_human_name]},
            "phone": {"validators": [validate_phone_number]},
        }

    def get_roles(self, obj: User) -> list[dict]:
        roles = getattr(obj, ACTIVE_API_ROLES_ATTR, None)
        if roles is None:
            roles = obj.user_roles.filter(is_active=True, role__is_active=True).select_related("role", "branch")
        return UserRoleSerializer(roles, many=True).data
