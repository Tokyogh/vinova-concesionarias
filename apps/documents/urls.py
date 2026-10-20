"""ES: Este módulo declara el enrutamiento URL para el dominio de documentos.

EN: This module declares URL routing for the documents domain.

Contexto existente / Existing context:
URL routing for the documents domain.
"""

from django.urls import path

from apps.documents.views import (
    AssetLibraryView,
    DocumentCatalogDataView,
    DocumentLibraryView,
    PrivateDocumentArchiveView,
    PrivateDocumentCreateView,
    PrivateDocumentDetailView,
    PrivateDocumentDownloadView,
    PrivateDocumentUpdateView,
    ReusableAssetArchiveView,
    ReusableAssetCreateView,
    ReusableAssetDetailView,
    ReusableAssetUpdateView,
)

app_name = "documents_internal"

urlpatterns = [
    path("", DocumentLibraryView.as_view(), name="list"),
    path("upload/", PrivateDocumentCreateView.as_view(), name="create"),
    path("catalog-data/", DocumentCatalogDataView.as_view(), name="catalog_data"),
    path("assets/", AssetLibraryView.as_view(), name="assets"),
    path("assets/upload/", ReusableAssetCreateView.as_view(), name="asset_create"),
    path("assets/<int:pk>/", ReusableAssetDetailView.as_view(), name="asset_detail"),
    path("assets/<int:pk>/edit/", ReusableAssetUpdateView.as_view(), name="asset_update"),
    path("assets/<int:pk>/archive/", ReusableAssetArchiveView.as_view(), name="asset_archive"),
    path("<int:pk>/", PrivateDocumentDetailView.as_view(), name="detail"),
    path("<int:pk>/edit/", PrivateDocumentUpdateView.as_view(), name="update"),
    path("<int:pk>/download/", PrivateDocumentDownloadView.as_view(), name="download"),
    path("<int:pk>/archive/", PrivateDocumentArchiveView.as_view(), name="archive"),
]
