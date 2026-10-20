"""ES: Este módulo registra modelos en la administración de Django para el dominio de cuentas.

EN: This module registers models in Django admin for the accounts domain.

Contexto existente / Existing context:
Django admin registrations for the accounts domain.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from apps.accounts.models import ClientInvitation, PermissionCode, Role, User, UserRole


class UserRoleInline(admin.TabularInline):
    model = UserRole
    fk_name = "user"
    extra = 0
    autocomplete_fields = ["role", "branch", "assigned_by"]


@admin.register(User)
class VinovaUserAdmin(UserAdmin):
    inlines = [UserRoleInline]
    list_display = ["username", "email", "first_name", "last_name", "branch", "is_active", "is_staff"]
    search_fields = ["username", "email", "first_name", "last_name"]
    list_filter = ["is_active", "is_staff", "is_superuser", "branch"]
    fieldsets = UserAdmin.fieldsets + (("Vinova Pro", {"fields": ("phone", "branch", "must_change_password", "failed_login_count", "locked_until", "last_password_change_at")}),)
    readonly_fields = ["last_login", "date_joined", "last_password_change_at"]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name", "code", "role_type", "level", "is_active"]
    search_fields = ["name", "code"]
    list_filter = ["role_type", "is_active"]
    filter_horizontal = ["permissions"]


@admin.register(PermissionCode)
class PermissionCodeAdmin(admin.ModelAdmin):
    list_display = ["module", "code", "name"]
    search_fields = ["module", "code", "name"]
    list_filter = ["module"]


@admin.register(UserRole)
class UserRoleAdmin(admin.ModelAdmin):
    list_display = ["user", "role", "branch", "is_active", "assigned_by", "starts_at", "expires_at"]
    search_fields = ["user__username", "user__email", "role__name", "role__code"]
    list_filter = ["is_active", "role", "branch"]
    autocomplete_fields = ["user", "role", "branch", "assigned_by"]


@admin.register(ClientInvitation)
class ClientInvitationAdmin(admin.ModelAdmin):
    list_display = ["email", "customer", "kind", "status", "expires_at", "accepted_at"]
    search_fields = ["email", "customer__first_name", "customer__last_name"]
    list_filter = ["kind", "status"]
    readonly_fields = ["token_digest", "accepted_at", "created_at", "updated_at"]
    autocomplete_fields = ["customer", "user", "invited_by"]
