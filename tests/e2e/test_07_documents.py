"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for 07 documents in the e2e domain.
"""

from __future__ import annotations

import re
import tempfile
from pathlib import Path

import pytest

from apps.documents.models import PrivateDocument
from tests.e2e.helpers.base import VinovaE2EBase
from tests.e2e.helpers.forms import submit_and_wait_for_url, wait_for_database_object

pytestmark = pytest.mark.e2e


class TestDocumentsReportsAndImportsFlow(VinovaE2EBase):
    def test_07_documents_reports_imports_and_help(self):
        self.login()
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as handle:
            handle.write(
                b"%PDF-1.4\n"
                b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
                b"2 0 obj<</Type/Pages/Count 0>>endobj\n"
                b"trailer<</Root 1 0 R>>\n%%EOF\n"
            )
            upload_path = handle.name
        try:
            self.page.goto(f"{self.live_server_url}/dashboard/documents/upload/")
            self.page.locator("input[name='title']").fill("Documento E2E")
            self.page.locator("select[name='document_type']").select_option("other")
            self.page.locator("input[name='file']").set_input_files(upload_path)
            self.page.locator("select[name='branch']").select_option(str(self.branch.pk))
            submit_and_wait_for_url(
                self.page,
                self.page.get_by_role("button", name="Guardar documento"),
                re.compile(r".*/dashboard/documents/\d+/$"),
                timeout=60_000,
            )
            document = wait_for_database_object(
                lambda: PrivateDocument.objects.get(title="Documento E2E"),
                description="el documento privado E2E",
            )
            assert document.branch_id == self.branch.pk
            assert Path(document.file.path).is_file()
            assert f"/dashboard/documents/{document.pk}/" in self.page.url
            assert self.page.get_by_role("heading", name="Documento E2E", level=1).is_visible()
        finally:
            Path(upload_path).unlink(missing_ok=True)

        for route in [
            "/dashboard/reports/",
            "/dashboard/imports/",
            "/dashboard/integrations/",
            "/dashboard/help/",
            "/dashboard/quality/",
        ]:
            response = self.page.goto(f"{self.live_server_url}{route}")
            assert response is not None and response.status < 400
