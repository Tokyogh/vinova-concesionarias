"""ES: Este módulo declara el enrutamiento URL para el dominio de importaciones.

EN: This module declares URL routing for the imports domain.

Contexto existente / Existing context:
URL routing for the imports domain.
"""

from django.urls import path

from apps.imports.views import ImportConfirmView, ImportCreateView, ImportDetailView, ImportHomeView, ImportRevalidateView, ImportTemplateDownloadView

app_name = "imports_internal"

urlpatterns = [
    path("", ImportHomeView.as_view(), name="home"),
    path("new/", ImportCreateView.as_view(), name="create"),
    path("templates/<slug:import_type>/", ImportTemplateDownloadView.as_view(), name="template"),
    path("<int:pk>/", ImportDetailView.as_view(), name="detail"),
    path("<int:pk>/revalidate/", ImportRevalidateView.as_view(), name="revalidate"),
    path("<int:pk>/confirm/", ImportConfirmView.as_view(), name="confirm"),
]
