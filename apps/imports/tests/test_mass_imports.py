"""ES: Este módulo especifica regresiones ejecutables para el dominio de importaciones.

EN: This module specifies executable regressions for the imports domain.

Contexto existente / Existing context:
Regression coverage for mass imports in the imports domain.
"""

import zipfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from openpyxl import Workbook, load_workbook

from apps.branches.models import Branch
from apps.companies.models import Company
from apps.customers.models import Customer
from apps.imports.models import ImportBatch
from apps.inventory.models import BranchStock, InventoryItem
from apps.vehicles.models import Vehicle, VehiclePartSpecification


class MassiveImportsTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser(username="admin", email="admin@example.com", password="pass12345")
        self.company = Company.objects.create(legal_name="Vinova Ecuador S.A.", commercial_name="Vinova", ruc="0999999999001")
        self.branch = Branch.objects.create(company=self.company, name="Quito Norte", code="quito-norte", city="Quito")

    def upload_csv(self, import_type, content, **extra):
        uploaded = SimpleUploadedFile("import.csv", content.encode("utf-8"), content_type="text/csv")
        self.client.force_login(self.user)
        payload = {"import_type": import_type, "original_file": uploaded, "notes": "test"}
        payload.update(extra)
        return self.client.post(reverse("imports_internal:create"), payload)

    def upload_xlsx(self, import_type, rows, **extra):
        workbook = Workbook()
        sheet = workbook.active
        for row in rows:
            sheet.append(row)
        output = BytesIO()
        workbook.save(output)
        workbook.close()
        uploaded = SimpleUploadedFile(
            "import.xlsx",
            output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.client.force_login(self.user)
        payload = {"import_type": import_type, "original_file": uploaded, "notes": "test"}
        payload.update(extra)
        return self.client.post(reverse("imports_internal:create"), payload)

    def test_vehicle_import_preview_and_confirm(self):
        csv_data = "marca,modelo,año,vin,placa,precio,estado,sucursal_codigo,publicar_en_catalogo,destacado,motor,garantia\nChevrolet,Camaro,2024,VINIMPORT001,ABC123,65000,Disponible,quito-norte,si,si,V8 6.2L,3 años\n"
        response = self.upload_csv(ImportBatch.ImportType.VEHICLES, csv_data)
        self.assertEqual(response.status_code, 302)
        batch = ImportBatch.objects.get()
        self.assertEqual(batch.status, ImportBatch.Status.VALIDATED)
        self.assertEqual(batch.valid_rows, 1)
        self.client.post(reverse("imports_internal:confirm", kwargs={"pk": batch.pk}))
        vehicle = Vehicle.objects.get(vin="VINIMPORT001")
        self.assertEqual(vehicle.branch, self.branch)
        self.assertTrue(vehicle.is_featured)
        self.assertIsNotNone(vehicle.published_at)
        self.assertTrue(VehiclePartSpecification.objects.filter(vehicle=vehicle, part_code=VehiclePartSpecification.PartCode.ENGINE).exists())
        batch.refresh_from_db()
        self.assertEqual(batch.created_count, 1)
        self.assertEqual(batch.status, ImportBatch.Status.COMPLETED)


    def test_vehicle_import_generates_internal_code_when_vin_is_blank(self):
        csv_data = "marca,modelo,año,vin,precio,estado,publicar_en_catalogo\nChevrolet,Trailblazer,2026,,42000,Disponible,si\n"
        self.upload_csv(ImportBatch.ImportType.VEHICLES, csv_data)
        batch = ImportBatch.objects.get()
        self.assertEqual(batch.status, ImportBatch.Status.VALIDATED)
        self.client.post(reverse("imports_internal:confirm", kwargs={"pk": batch.pk}))
        vehicle = Vehicle.objects.get(model__name="Trailblazer")
        self.assertIsNone(vehicle.vin)
        self.assertEqual(vehicle.internal_code, "VIN-CHEVROLET-TRAILBLAZER-2026")
        self.assertIsNotNone(vehicle.published_at)

    def test_vehicle_import_respects_publish_catalog_no(self):
        csv_data = "marca,modelo,año,vin,precio,estado,publicar_en_catalogo\nChevrolet,Onix,2025,VINIMPORTPRIVATE,23000,Disponible,no\n"
        self.upload_csv(ImportBatch.ImportType.VEHICLES, csv_data)
        batch = ImportBatch.objects.get()
        self.client.post(reverse("imports_internal:confirm", kwargs={"pk": batch.pk}))

        vehicle = Vehicle.objects.get(vin="VINIMPORTPRIVATE")
        self.assertEqual(vehicle.status, Vehicle.Status.AVAILABLE)
        self.assertIsNone(vehicle.published_at)

        response = self.client.get(reverse("vehicles:catalog"))
        self.assertNotContains(response, "VINIMPORTPRIVATE")

    def test_vehicle_import_can_unpublish_existing_vehicle(self):
        csv_public = "marca,modelo,año,vin,precio,estado,publicar_en_catalogo\nChevrolet,Onix,2025,VINIMPORTTOGGLE,23000,Disponible,si\n"
        self.upload_csv(ImportBatch.ImportType.VEHICLES, csv_public)
        first_batch = ImportBatch.objects.get()
        self.client.post(reverse("imports_internal:confirm", kwargs={"pk": first_batch.pk}))
        self.assertIsNotNone(Vehicle.objects.get(vin="VINIMPORTTOGGLE").published_at)

        csv_private = "marca,modelo,año,vin,precio,estado,publicar_en_catalogo\nChevrolet,Onix,2025,VINIMPORTTOGGLE,23000,Disponible,no\n"
        self.upload_csv(ImportBatch.ImportType.VEHICLES, csv_private)
        second_batch = ImportBatch.objects.order_by("-id").first()
        self.client.post(reverse("imports_internal:confirm", kwargs={"pk": second_batch.pk}))

        vehicle = Vehicle.objects.get(vin="VINIMPORTTOGGLE")
        self.assertIsNone(vehicle.published_at)
        self.assertEqual(second_batch.rows.first().normalized_payload["publish_catalog"], False)

    def test_vehicle_import_rejects_duplicate_vin_inside_file(self):
        csv_data = (
            "marca,modelo,año,vin,precio,estado\n"
            "Chevrolet,Onix,2025,VINDUPLICATE001,23000,Disponible\n"
            "Chevrolet,Tracker,2025,VINDUPLICATE001,29000,Disponible\n"
        )
        self.upload_csv(ImportBatch.ImportType.VEHICLES, csv_data)
        batch = ImportBatch.objects.get()
        self.assertEqual(batch.status, ImportBatch.Status.FAILED)
        self.assertEqual(batch.invalid_rows, 2)
        self.assertFalse(batch.can_confirm)
        self.assertIn("VIN duplicado", batch.rows.first().errors[0])

    def test_vehicle_import_rejects_invalid_status_and_boolean(self):
        csv_data = "marca,modelo,año,vin,precio,estado,publicar_en_catalogo\nChevrolet,Onix,2025,VININVALIDVALUES,23000,En patio,talvez\n"
        self.upload_csv(ImportBatch.ImportType.VEHICLES, csv_data)
        batch = ImportBatch.objects.get()
        self.assertEqual(batch.status, ImportBatch.Status.FAILED)
        errors = " ".join(batch.rows.first().errors)
        self.assertIn("Estado no reconocido", errors)
        self.assertIn("usa únicamente sí o no", errors)

    def test_vehicle_import_rejects_contextually_invalid_values(self):
        csv_data = (
            "marca,modelo,año,vin,placa,precio,estado\n"
            "Chevrolet,Onix,2025.5,VIN?,123-ABC,NaN,Disponible\n"
        )
        self.upload_csv(ImportBatch.ImportType.VEHICLES, csv_data)

        batch = ImportBatch.objects.get()
        errors = " ".join(batch.rows.first().errors)
        self.assertEqual(batch.status, ImportBatch.Status.FAILED)
        self.assertIn("Valor entero inválido", errors)
        self.assertIn("VIN/chasis", errors)
        self.assertIn("placa válida", errors)
        self.assertIn("Valor decimal inválido", errors)

    def test_customer_import_rejects_invalid_identity_and_contact_fields(self):
        csv_data = (
            "tipo,identificacion_tipo,identificacion,nombres,email,telefono\n"
            "natural,cedula,0102030405,Cliente 123,no-es-correo,ABC\n"
        )
        self.upload_csv(ImportBatch.ImportType.CUSTOMERS, csv_data)

        batch = ImportBatch.objects.get()
        errors = " ".join(batch.rows.first().errors)
        self.assertEqual(batch.status, ImportBatch.Status.FAILED)
        self.assertIn("nombre contiene caracteres", errors)
        self.assertIn("correo electrónico válida", errors)
        self.assertIn("Usa únicamente dígitos", errors)
        self.assertIn("cédula ecuatoriana válida", errors)

    def test_inventory_import_rejects_negative_or_non_finite_money(self):
        csv_data = (
            "sku,nombre,precio,costo\n"
            "ITEM-NEGATIVO,Artículo de prueba,-1,Infinity\n"
        )
        self.upload_csv(ImportBatch.ImportType.INVENTORY, csv_data)

        batch = ImportBatch.objects.get()
        errors = " ".join(batch.rows.first().errors)
        self.assertEqual(batch.status, ImportBatch.Status.FAILED)
        self.assertIn("Valor decimal inválido", errors)

    def test_stock_import_rejects_negative_minimum_stock(self):
        InventoryItem.objects.create(sku="ITEM-STOCK", name="Artículo", price=0)
        csv_data = (
            "sku,sucursal_codigo,cantidad,stock_minimo\n"
            "ITEM-STOCK,quito-norte,10,-1\n"
        )
        self.upload_csv(ImportBatch.ImportType.STOCK, csv_data)

        batch = ImportBatch.objects.get()
        self.assertEqual(batch.status, ImportBatch.Status.FAILED)
        self.assertIn("no puede ser negativo", " ".join(batch.rows.first().errors))

    def test_empty_vehicle_file_cannot_be_confirmed(self):
        self.upload_csv(ImportBatch.ImportType.VEHICLES, "marca,modelo,año,vin\n")
        batch = ImportBatch.objects.get()
        self.assertEqual(batch.status, ImportBatch.Status.FAILED)
        self.assertEqual(batch.total_rows, 0)
        self.assertFalse(batch.can_confirm)
        self.assertIn("no contiene filas", batch.errors[0]["errors"][0])

    @override_settings(VINOVA_IMPORT_MAX_ROWS=1)
    def test_csv_import_rejects_rows_above_configured_limit(self):
        csv_data = (
            "marca,modelo,año,vin\n"
            "Chevrolet,Onix,2025,VINLIMIT001\n"
            "Chevrolet,Tracker,2025,VINLIMIT002\n"
        )
        response = self.upload_csv(ImportBatch.ImportType.VEHICLES, csv_data)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "máximo permitido de 1 filas")
        self.assertFalse(ImportBatch.objects.filter(original_filename="import.csv").exists())

    @override_settings(VINOVA_IMPORT_MAX_COLUMNS=3)
    def test_csv_import_rejects_columns_above_configured_limit(self):
        response = self.upload_csv(
            ImportBatch.ImportType.VEHICLES,
            "marca,modelo,año,vin\nChevrolet,Onix,2025,VINLIMIT003\n",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "máximo permitido de 3 columnas")
        self.assertFalse(ImportBatch.objects.filter(original_filename="import.csv").exists())

    def test_csv_import_rejects_rows_wider_than_declared_header(self):
        response = self.upload_csv(
            ImportBatch.ImportType.VEHICLES,
            "marca,modelo,año\nChevrolet,Onix,2025,VINUNDECLARED\n",
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "contiene más columnas que el encabezado")
        self.assertFalse(ImportBatch.objects.filter(original_filename="import.csv").exists())

    @override_settings(VINOVA_IMPORT_MAX_ROWS=1)
    def test_xlsx_import_rejects_rows_above_configured_limit(self):
        response = self.upload_xlsx(
            ImportBatch.ImportType.VEHICLES,
            [
                ["marca", "modelo", "año", "vin"],
                ["Chevrolet", "Onix", 2025, "VINLIMIT004"],
                ["Chevrolet", "Tracker", 2025, "VINLIMIT005"],
            ],
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "máximo permitido de 1 filas")
        self.assertFalse(ImportBatch.objects.filter(original_filename="import.xlsx").exists())

    @override_settings(VINOVA_IMPORT_MAX_COLUMNS=3)
    def test_xlsx_import_rejects_columns_above_configured_limit(self):
        response = self.upload_xlsx(
            ImportBatch.ImportType.VEHICLES,
            [["marca", "modelo", "año", "vin"], ["Chevrolet", "Onix", 2025, "VINLIMIT006"]],
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "máximo permitido de 3 columnas")
        self.assertFalse(ImportBatch.objects.filter(original_filename="import.xlsx").exists())

    def test_xlsx_import_rejects_incomplete_office_container_without_residue(self):
        output = BytesIO()
        with zipfile.ZipFile(output, "w") as archive:
            archive.writestr("[Content_Types].xml", b"<Types/>")
            archive.writestr("xl/workbook.xml", b"<workbook/>")
        uploaded = SimpleUploadedFile(
            "import.xlsx",
            output.getvalue(),
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.client.force_login(self.user)

        response = self.client.post(
            reverse("imports_internal:create"),
            {"import_type": ImportBatch.ImportType.VEHICLES, "original_file": uploaded},
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "no tiene una estructura válida")
        self.assertFalse(ImportBatch.objects.filter(original_filename="import.xlsx").exists())

    def test_customer_import_does_not_require_branch(self):
        csv_data = "tipo,identificacion_tipo,identificacion,nombres,apellidos,email,ciudad,provincia\nnatural,cedula,2458963176,Pepe,Mora,pepe@example.com,Guayaquil,Guayas\n"
        response = self.upload_csv(ImportBatch.ImportType.CUSTOMERS, csv_data)
        self.assertEqual(response.status_code, 302)
        batch = ImportBatch.objects.get()
        self.assertEqual(batch.valid_rows, 1)
        self.client.post(reverse("imports_internal:confirm", kwargs={"pk": batch.pk}))
        customer = Customer.objects.get(identification_number="2458963176")
        self.assertEqual(customer.city, "Guayaquil")
        self.assertIsNone(customer.assigned_branch)

    def test_inventory_and_stock_import(self):
        item_csv = "sku,nombre,categoria,tipo_articulo,precio,costo,publico,controla_stock\nACEITE-5W30,Aceite 5W30,Aceites,aceite,12.50,8.00,si,si\n"
        self.upload_csv(ImportBatch.ImportType.INVENTORY, item_csv)
        item_batch = ImportBatch.objects.get(import_type=ImportBatch.ImportType.INVENTORY)
        self.client.post(reverse("imports_internal:confirm", kwargs={"pk": item_batch.pk}))
        self.assertTrue(InventoryItem.objects.filter(sku="ACEITE-5W30").exists())

        stock_csv = "sku,sucursal_codigo,cantidad,stock_minimo,ubicacion\nACEITE-5W30,quito-norte,50,10,Bodega A\n"
        self.upload_csv(ImportBatch.ImportType.STOCK, stock_csv)
        stock_batch = ImportBatch.objects.get(import_type=ImportBatch.ImportType.STOCK)
        self.client.post(reverse("imports_internal:confirm", kwargs={"pk": stock_batch.pk}))
        stock = BranchStock.objects.get(item__sku="ACEITE-5W30", branch=self.branch)
        self.assertEqual(str(stock.quantity), "50.00")
        self.assertEqual(str(stock.minimum_stock), "10.00")

    def test_vehicle_import_can_use_default_branch(self):
        csv_data = "marca,modelo,año,vin,precio,estado\nChevrolet,Tracker,2025,VINIMPORTDEFAULT,29000,Disponible\n"
        response = self.upload_csv(ImportBatch.ImportType.VEHICLES, csv_data, default_branch=str(self.branch.pk), require_vehicle_branch="on")
        self.assertEqual(response.status_code, 302)
        batch = ImportBatch.objects.get(original_filename="import.csv")
        self.assertEqual(batch.default_branch, self.branch)
        self.assertEqual(batch.valid_rows, 1)
        self.client.post(reverse("imports_internal:confirm", kwargs={"pk": batch.pk}))
        self.assertEqual(Vehicle.objects.get(vin="VINIMPORTDEFAULT").branch, self.branch)

    def test_import_original_file_uses_private_storage(self):
        csv_data = "marca,modelo,año,vin,precio,estado\nChevrolet,Spark,2023,VINPRIVATE001,12000,Disponible\n"
        self.upload_csv(ImportBatch.ImportType.VEHICLES, csv_data)
        batch = ImportBatch.objects.get()
        self.assertIn(str(settings.PRIVATE_STORAGE_ROOT), str(batch.original_file.storage.location))
        self.assertTrue(batch.original_file.name.startswith("imports/originals/"))

    def test_imports_home_and_template_are_protected(self):
        response = self.client.get(reverse("imports_internal:home"))
        self.assertEqual(response.status_code, 302)
        self.client.force_login(self.user)
        response = self.client.get(reverse("imports_internal:home"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Importaciones masivas")
        template = self.client.get(reverse("imports_internal:template", kwargs={"import_type": "vehicles"}))
        self.assertEqual(template.status_code, 200)
        self.assertIn("text/csv", template["Content-Type"])
        self.assertContains(template, "publicar_en_catalogo")
        xlsx_template = self.client.get(reverse("imports_internal:template", kwargs={"import_type": "vehicles"}) + "?format=xlsx")
        self.assertEqual(xlsx_template.status_code, 200)
        self.assertIn("spreadsheetml", xlsx_template["Content-Type"])
        workbook = load_workbook(BytesIO(xlsx_template.content))
        self.assertEqual(workbook.sheetnames, ["datos", "instrucciones", "ejemplo", "sucursales", "valores_validos"])
        self.assertEqual(workbook["datos"].freeze_panes, "A2")
        self.assertIsNone(workbook["datos"]["A2"].value)
        self.assertEqual(workbook["ejemplo"]["A2"].value, "Chevrolet")
        self.assertEqual(workbook["datos"]["A1"].fill.fgColor.rgb[-6:], "1F4E78")

    def test_vehicle_list_has_direct_import_action(self):
        self.client.force_login(self.user)
        response = self.client.get(reverse("vehicles_internal:list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Importar vehículos")
