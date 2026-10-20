"""ES: Genera mapas visuales anotados con datos sintéticos y rutas reales.

EN: Generates annotated functional maps with synthetic data and real routes.

Contexto existente / Existing context:
Controlled Chromium evidence for the F17 functional-map documentation.
"""

from __future__ import annotations

import os
from datetime import timedelta
from decimal import Decimal
from pathlib import Path

import pytest
from django.conf import settings
from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import PermissionCode, Role, User, UserRole
from apps.documents.models import PrivateDocument
from apps.help_center.models import HelpArticle, HelpCategory
from apps.inventory.models import BranchStock
from apps.invoices.models import InvoiceRecord
from apps.notifications.models import NotificationMessage, NotificationRecipient
from apps.post_sales.models import ServiceOrder
from apps.privacy.cookies import encode_cookie_preferences
from apps.sales.models import SaleRecord
from apps.vehicles.models import CustomerVehicle
from tests.e2e.helpers.assertions import assert_no_document_overflow
from tests.e2e.helpers.base import VinovaE2EBase


pytestmark = pytest.mark.e2e


@override_settings(VINOVA_MODULE_POST_SALES_ENABLED=True)
class TestFunctionalMaps(VinovaE2EBase):
    """ES: Captura las interfaces F17 sin datos personales ni persistencia empresarial.

    EN: Captures F17 interfaces without personal data or business persistence.
    """

    def setUp(self):
        super().setUp()
        self.output_root = Path(
            os.getenv("VINOVA_FUNCTIONAL_MAP_ROOT", str(self.artifact_root / "functional-maps"))
        )
        self.output_root.mkdir(parents=True, exist_ok=True)
        self._set_consent_cookie()
        self._create_visual_data()

    def _set_consent_cookie(self):
        """ES: Habilita medios externos en este contexto aislado, sin cambiar preferencias reales.

        EN: Enables external media in this isolated context without changing real preferences.
        """

        self.context.add_cookies(
            [
                {
                    "name": settings.VINOVA_COOKIE_CONSENT_NAME,
                    "value": encode_cookie_preferences(
                        preferences=True,
                        analytics=False,
                        external_media=True,
                    ),
                    "url": self.live_server_url,
                }
            ]
        )

    def _create_visual_data(self):
        """ES: Prepara únicamente registros sintéticos dentro de la base temporal E2E.

        EN: Prepares synthetic records only inside the temporary E2E database.
        """

        self.branch.address = "Av. de Pruebas 100, Quito"
        self.branch.province = "Pichincha"
        self.branch.phone = "+593 2 555 0100"
        self.branch.opening_hours = "Lun–Vie 08:30–17:30"
        self.branch.description = "Sede sintética para documentación visual controlada."
        self.branch.services = ["Venta de vehículos", "Atención postventa", "Repuestos"]
        self.branch.latitude = Decimal("-0.180653")
        self.branch.longitude = Decimal("-78.467834")
        self.branch.save()

        portal_permission, _ = PermissionCode.objects.get_or_create(
            code="portal.access",
            defaults={"module": "portal", "name": "Acceso al portal"},
        )
        portal_role = Role.objects.create(code="f17-visual-client", name="Cliente visual F17")
        portal_role.permissions.add(portal_permission)
        self.portal_user = User.objects.create_user(
            username="cliente-visual-f17",
            email="cliente.visual.f17@example.com",
            password=self.password,
            first_name="Cliente",
            last_name="Visual F17",
        )
        UserRole.objects.create(user=self.portal_user, role=portal_role)
        self.customer.account = self.portal_user
        self.customer.status = self.customer.Status.ACTIVE
        self.customer.address = "Dirección sintética de pruebas"
        self.customer.city = "Quito"
        self.customer.province = "Pichincha"
        self.customer.save()

        self.vehicle.mileage = 24000
        self.vehicle.plate = "QAA-0001"
        self.vehicle.color = "Azul"
        self.vehicle.save()
        self.vehicle_link = CustomerVehicle.objects.create(
            customer=self.customer,
            vehicle=self.vehicle,
            initial_mileage=self.vehicle.mileage,
            snapshot_customer_name=self.customer.display_name,
            snapshot_identification="SINTÉTICO",
        )

        now = timezone.now()
        self.completed_service = ServiceOrder.objects.create(
            number="OT-F17-0001",
            branch=self.branch,
            customer=self.customer,
            vehicle=self.vehicle,
            responsible=self.admin,
            status=ServiceOrder.Status.COMPLETED,
            description="Mantenimiento preventivo sintético",
            scheduled_at=now - timedelta(days=35),
            completed_at=now - timedelta(days=34),
            reception_mileage=22000,
            delivery_mileage=22100,
            next_service_date=timezone.localdate() + timedelta(days=90),
            next_service_mileage=27000,
            total_cost=Decimal("180.00"),
            created_by=self.admin,
        )
        self.upcoming_service = ServiceOrder.objects.create(
            number="OT-F17-0002",
            branch=self.branch,
            customer=self.customer,
            vehicle=self.vehicle,
            responsible=self.admin,
            status=ServiceOrder.Status.SCHEDULED,
            description="Revisión programada sintética",
            scheduled_at=now + timedelta(days=18),
            reception_mileage=24000,
            next_service_date=timezone.localdate() + timedelta(days=18),
            next_service_mileage=27000,
            created_by=self.admin,
        )

        self.document = PrivateDocument.objects.create(
            title="Garantía sintética F17",
            document_type=PrivateDocument.DocumentType.WARRANTY,
            file="documents/warranty/f17-synthetic.pdf",
            status=PrivateDocument.Status.ACTIVE,
            branch=self.branch,
            customer=self.customer,
            vehicle=self.vehicle,
            original_name="garantia-sintetica-f17.pdf",
            mime_type="application/pdf",
            size_bytes=1024,
            uploaded_by=self.admin,
        )
        self.sale = SaleRecord.objects.create(
            number="COT-F17-0001",
            kind=SaleRecord.Kind.QUOTE,
            status=SaleRecord.Status.QUOTED,
            customer=self.customer,
            branch=self.branch,
            advisor=self.admin,
            vehicle=self.vehicle,
            source=SaleRecord.Source.SHOWROOM,
            vehicle_price=Decimal("35000.00"),
            subtotal=Decimal("35000.00"),
            tax_total=Decimal("5250.00"),
            total=Decimal("40250.00"),
            balance_due=Decimal("40250.00"),
            valid_until=timezone.localdate() + timedelta(days=7),
            created_by=self.admin,
        )
        self.invoice = InvoiceRecord.objects.create(
            number="FAC-QA-MTR-000001",
            invoice_type=InvoiceRecord.InvoiceType.INVOICE,
            status=InvoiceRecord.Status.ISSUED,
            sale=self.sale,
            company=self.company,
            branch=self.branch,
            customer=self.customer,
            customer_name=self.customer.display_name,
            customer_email=self.customer.email,
            customer_phone=self.customer.phone,
            subtotal=Decimal("35000.00"),
            tax_total=Decimal("5250.00"),
            total=Decimal("40250.00"),
            balance_due=Decimal("40250.00"),
            created_by=self.admin,
            issued_by=self.admin,
            issued_at=now,
        )
        notification = NotificationMessage.objects.create(
            title="Próxima revisión programada",
            body="Mensaje sintético para explicar el origen de las alertas del portal.",
            message_type=NotificationMessage.MessageType.MAINTENANCE,
            related_customer=self.customer,
            related_vehicle=self.vehicle,
            sender=self.admin,
            created_by=self.admin,
            dedup_key="f17-functional-map-notification",
        )
        NotificationRecipient.objects.create(
            notification=notification,
            recipient_type=NotificationRecipient.RecipientType.CUSTOMER,
            customer=self.customer,
            display_name_snapshot="Cliente Visual F17",
            email_snapshot="cliente.visual.f17@example.com",
        )
        BranchStock.objects.create(
            item=self.item,
            branch=self.branch,
            quantity=Decimal("4.00"),
            reserved_quantity=Decimal("1.00"),
            minimum_stock=Decimal("5.00"),
            location_code="QA-A-01",
        )
        help_category = HelpCategory.objects.create(
            name="Operación F17",
            slug="operacion-f17",
            description="Contenido sintético de documentación visual.",
            icon="?",
            order=1,
        )
        HelpArticle.objects.create(
            category=help_category,
            title="Gestionar un vehículo de forma segura",
            slug="gestionar-vehiculo-f17",
            summary="Guía sintética visible únicamente durante la prueba controlada.",
            content="Revisa permisos, sucursal y estado antes de guardar cambios.",
            article_type=HelpArticle.ArticleType.CONTEXT,
            route_name="vehicles_internal:detail",
            is_featured=True,
            is_published=True,
            updated_by=self.admin,
        )

    def _capture(self, filename: str, route: str, annotations: list[tuple[str, str]]):
        """ES: Abre una ruta real, agrega leyendas temporales y captura la página completa.

        EN: Opens a real route, adds temporary legends, and captures the full page.
        """

        response = self.page.goto(f"{self.live_server_url}{route}", wait_until="networkidle")
        assert response is not None and response.status == 200, route
        viewport = self.page.viewport_size
        assert viewport is not None
        assert_no_document_overflow(self.page, route, viewport)
        for selector, _label in annotations:
            assert self.page.locator(selector).count() >= 1, f"Falta {selector} en {route}"
        self.page.evaluate(
            """
            annotations => {
              document.querySelectorAll('[data-f17-map-overlay]').forEach(node => node.remove());
              const legend = document.createElement('aside');
              legend.dataset.f17MapOverlay = '1';
              Object.assign(legend.style, {
                position: 'absolute', zIndex: '2147483645', top: '92px', right: '20px', width: '310px',
                padding: '14px', border: '1px solid #88bfe5', borderRadius: '12px', color: '#123b5a',
                font: '600 13px/1.35 Arial, sans-serif', background: '#f7fcffff',
                boxShadow: '0 8px 28px #001c3438'
              });
              const heading = document.createElement('strong');
              heading.textContent = 'Mapa funcional F17 · datos sintéticos';
              Object.assign(heading.style, {display: 'block', marginBottom: '8px', fontSize: '14px'});
              legend.appendChild(heading);
              annotations.forEach((item, index) => {
                const target = document.querySelector(item.selector);
                const rect = target.getBoundingClientRect();
                const badge = document.createElement('span');
                badge.dataset.f17MapOverlay = '1';
                badge.textContent = String(index + 1);
                Object.assign(badge.style, {
                  position: 'absolute', zIndex: '2147483646', display: 'grid', placeItems: 'center',
                  width: '30px', height: '30px', border: '3px solid #fff', borderRadius: '999px',
                  color: '#fff', font: '800 14px/1 Arial, sans-serif', background: '#006bc7',
                  boxShadow: '0 3px 12px #001c3480',
                  left: `${Math.max(8, rect.left + window.scrollX + 8)}px`,
                  top: `${Math.max(8, rect.top + window.scrollY + 8)}px`
                });
                document.body.appendChild(badge);
                const row = document.createElement('span');
                Object.assign(row.style, {display: 'flex', alignItems: 'center', marginTop: '5px'});
                const number = document.createElement('b');
                number.textContent = String(index + 1);
                Object.assign(number.style, {
                  display: 'inline-grid', placeItems: 'center', flex: '0 0 22px', width: '22px',
                  height: '22px', marginRight: '7px', borderRadius: '999px', color: '#fff',
                  background: '#006bc7'
                });
                row.appendChild(number);
                row.appendChild(document.createTextNode(item.label));
                legend.appendChild(row);
              });
              document.body.appendChild(legend);
            }
            """,
            [{"selector": selector, "label": label} for selector, label in annotations],
        )
        self.page.screenshot(path=str(self.output_root / filename), full_page=True)
        self.page.evaluate(
            "document.querySelectorAll('[data-f17-map-overlay]').forEach(node => node.remove())"
        )

    def _login_portal(self):
        """ES: Autentica al cliente y espera su destino privado, distinto del dashboard Staff.

        EN: Authenticates the client and waits for its private destination, unlike the Staff dashboard.
        """

        self.page.goto(f"{self.live_server_url}/accounts/login/")
        self.page.locator("input[name='username']").fill(self.portal_user.username)
        self.page.locator("input[name='password']").fill(self.password)
        self.page.get_by_role("button", name="Ingresar").click()
        self.page.wait_for_url(f"{self.live_server_url}/mi-cuenta/")

    def test_12_generate_functional_maps(self):
        """ES: Documenta los catorce recorridos iniciales y separa documentos de facturas.

        EN: Documents the fourteen initial flows and separates documents from invoices.
        """

        self.page.set_viewport_size({"width": 1440, "height": 1000})
        self._capture(
            "09-instituciones-mapa.png",
            "/instituciones/",
            [
                (".institution-selector", "Tipos y conteos publicados"),
                (".institutions-list", "Sedes autorizadas y filtrables"),
                (".institutions-map", "Mapa externo o fallback controlado"),
                (".institution-detail-panel", "Detalle de la sede seleccionada"),
            ],
        )

        self._login_portal()
        portal_captures = [
            (
                "01-dashboard-cliente.png",
                "/mi-cuenta/",
                [
                    (".portal-sidebar", "Navegación privada autorizada"),
                    (".portal-metrics", "Resumen calculado del expediente"),
                    (".portal-home-grid", "Vehículos, servicios y actividad"),
                ],
            ),
            (
                "02-indicadores-mantenimiento.png",
                "/mi-cuenta/",
                [
                    (".portal-metrics", "Indicadores derivados, no editables aquí"),
                    (".portal-upcoming-panel", "Órdenes programadas"),
                    (".portal-chart-panel", "Servicios completados por mes"),
                ],
            ),
            (
                "03-perfil-cliente.png",
                "/mi-cuenta/perfil/",
                [
                    (".portal-grid", "Resumen de cuenta y expediente"),
                    (".portal-profile-form", "Campos de contacto editables"),
                ],
            ),
            (
                "04-mis-vehiculos.png",
                "/mi-cuenta/vehiculos/",
                [
                    (".portal-toolbar", "Búsqueda dentro del ownership"),
                    (".portal-garage-grid", "Vehículos vinculados al cliente"),
                ],
            ),
            (
                "05-vinculacion-codigo.png",
                "/mi-cuenta/vehiculos/agregar/",
                [
                    (".portal-redeem-card", "Canje privado sin kilometraje"),
                    ("[data-vnv-code]", "Entrada VNV formateada y validada"),
                ],
            ),
            (
                "06-historial-servicios.png",
                "/mi-cuenta/servicios/?view=history",
                [
                    (".portal-filter-form", "Filtros acotados al expediente"),
                    (".portal-service-list", "Órdenes visibles para el vehículo propio"),
                ],
            ),
            (
                "07-documentos.png",
                "/mi-cuenta/documentos/",
                [
                    (".portal-filter-form", "Filtros documentales"),
                    (".portal-document-grid", "Documentos privados autorizados"),
                ],
            ),
            (
                "07b-facturas.png",
                "/mi-cuenta/facturas/",
                [
                    (".portal-filter-form", "Filtros de comprobantes"),
                    (".portal-invoice-list", "Facturas emitidas del cliente"),
                ],
            ),
            (
                "08-notificaciones.png",
                "/mi-cuenta/notificaciones/",
                [
                    (".portal-filter-form", "Búsqueda y estado de entrega"),
                    (".portal-notifications", "Mensajes destinados al expediente"),
                ],
            ),
        ]
        for filename, route, callouts in portal_captures:
            self._capture(filename, route, callouts)

        self.context.clear_cookies()
        self._set_consent_cookie()
        self.login(self.admin)
        staff_captures = [
            (
                "10-dashboard-staff.png",
                "/dashboard/admin/",
                [
                    ("#staff-sidebar", "Módulos permitidos por RBAC"),
                    (".adaptive-metric", "Indicadores operativos agregados"),
                    (".adaptive-widget--actions", "Acciones autorizadas"),
                ],
            ),
            (
                "11-inventario.png",
                "/dashboard/inventory/",
                [
                    (".inventory-status-grid", "Totales y alertas de stock"),
                    (".inventory-item-table", "Stock agregado por artículo"),
                    (".inventory-movement-table", "Movimientos auditables"),
                ],
            ),
            (
                "12-ventas.png",
                "/dashboard/sales/",
                [
                    (".sales-status-grid", "Estado agregado del pipeline"),
                    (".table-panel", "Operaciones filtradas por alcance"),
                ],
            ),
            (
                "13-administracion-vehiculo.png",
                f"/dashboard/vehicles/{self.vehicle.pk}/",
                [
                    (".vehicle-summary-card", "Identidad y ficha técnica"),
                    (".vehicle-media-upload-card", "Multimedia reutilizable"),
                    (".vehicle-internal-detail", "Estado y acciones autorizadas"),
                ],
            ),
            (
                "14-ayuda-contextual.png",
                "/dashboard/help/",
                [
                    (".help-search-hero", "Búsqueda limitada al contenido visible"),
                    (".help-card-grid", "Artículos destacados autorizados"),
                    (".help-category-stack", "Biblioteca administrable y versionada"),
                ],
            ),
        ]
        for filename, route, callouts in staff_captures:
            self._capture(filename, route, callouts)

        expected = {item[0] for item in portal_captures + staff_captures}
        expected.add("09-instituciones-mapa.png")
        assert expected == {path.name for path in self.output_root.glob("*.png")}
