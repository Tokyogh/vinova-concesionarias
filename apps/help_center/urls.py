"""ES: Este módulo declara el enrutamiento URL para el dominio de ayuda.

EN: This module declares URL routing for the help center domain.

Contexto existente / Existing context:
URL routing for the help center domain.
"""

from django.urls import path

from apps.help_center.views import (
    HelpArticleDetailView,
    HelpArticleHistoryView,
    HelpArticleManageFormView,
    HelpArticleManageListView,
    HelpArticleManagePreviewView,
    HelpArticlePublicationView,
    HelpArticlePrintView,
    HelpArticleRestoreView,
    HelpChecklistDetailView,
    HelpHomeView,
    HelpSearchView,
    ToggleChecklistItemView,
    ToggleTrainingModeView,
)

app_name = "help_center"

urlpatterns = [
    path("", HelpHomeView.as_view(), name="home"),
    path("search/", HelpSearchView.as_view(), name="search"),
    path("articles/<slug:slug>/", HelpArticleDetailView.as_view(), name="article"),
    path("articles/<slug:slug>/print/", HelpArticlePrintView.as_view(), name="article_print"),
    path("checklists/<slug:slug>/", HelpChecklistDetailView.as_view(), name="checklist"),
    path("checklists/items/<int:item_id>/toggle/", ToggleChecklistItemView.as_view(), name="toggle_item"),
    path("training-mode/", ToggleTrainingModeView.as_view(), name="training_mode"),
    path("manage/articles/", HelpArticleManageListView.as_view(), name="manage_articles"),
    path("manage/articles/new/", HelpArticleManageFormView.as_view(), name="manage_create"),
    path("manage/articles/<int:pk>/edit/", HelpArticleManageFormView.as_view(), name="manage_edit"),
    path("manage/articles/<int:pk>/preview/", HelpArticleManagePreviewView.as_view(), name="manage_preview"),
    path("manage/articles/<int:pk>/history/<int:version_pk>/restore/", HelpArticleRestoreView.as_view(), name="manage_restore"),
    path("manage/articles/<int:pk>/history/", HelpArticleHistoryView.as_view(), name="manage_history"),
    path("manage/articles/<int:pk>/<str:action>/", HelpArticlePublicationView.as_view(), name="manage_publication"),
]
