"""ES: Este módulo registra modelos en la administración de Django para el dominio de ayuda.

EN: This module registers models in Django admin for the help center domain.

Contexto existente / Existing context:
Django admin registrations for the help center domain.
"""

from django.contrib import admin

from apps.help_center.models import (
    HelpArticle,
    HelpArticleVersion,
    HelpCategory,
    HelpChecklist,
    HelpChecklistItem,
    UserChecklistProgress,
    UserHelpPreference,
)


class HelpChecklistItemInline(admin.TabularInline):
    model = HelpChecklistItem
    extra = 0


@admin.register(HelpCategory)
class HelpCategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name", "description")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(HelpArticle)
class HelpArticleAdmin(admin.ModelAdmin):
    list_display = ("title", "category", "article_type", "route_name", "is_published")
    list_filter = ("article_type", "category", "is_featured", "is_published")
    search_fields = ("title", "summary", "content", "keywords")
    prepopulated_fields = {"slug": ("title",)}


@admin.register(HelpArticleVersion)
class HelpArticleVersionAdmin(admin.ModelAdmin):
    list_display = ("article", "version", "is_published", "created_by", "created_at")
    list_filter = ("is_published", "article_type", "category")
    search_fields = ("article__title", "title", "change_note")
    readonly_fields = [field.name for field in HelpArticleVersion._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(HelpChecklist)
class HelpChecklistAdmin(admin.ModelAdmin):
    list_display = ("title", "permission_code", "order", "is_published")
    list_filter = ("is_published",)
    search_fields = ("title", "summary")
    prepopulated_fields = {"slug": ("title",)}
    inlines = [HelpChecklistItemInline]


@admin.register(UserChecklistProgress)
class UserChecklistProgressAdmin(admin.ModelAdmin):
    list_display = ("user", "item", "completed_at")
    search_fields = ("user__username", "item__title")


@admin.register(UserHelpPreference)
class UserHelpPreferenceAdmin(admin.ModelAdmin):
    list_display = ("user", "training_mode", "updated_at")
    search_fields = ("user__username", "user__email")
