"""ES: Implementa el comando administrativo «seed api scopes» para API e integraciones.

EN: Implements the «seed api scopes» management command for api.

Contexto existente / Existing context:
Django management command for seed api scopes.
"""

from django.core.management.base import BaseCommand

from apps.api.models import APIScope


SCOPES = {
    "*": ("Acceso total", "Solo para integraciones altamente controladas.", True),
    "api:read": ("API base: lectura", "Lectura de endpoints generales.", False),
    "api:write": ("API base: escritura", "Escritura de endpoints generales.", True),
    "users:read": ("Usuarios: lectura", "Consulta de usuarios y roles.", True),
    "users:write": ("Usuarios: escritura", "Administración de usuarios y roles.", True),
    "companies:read": ("Empresa: lectura", "Consulta de la empresa propietaria.", True),
    "companies:write": ("Empresa: escritura", "Actualización de empresa.", True),
    "branches:read": ("Sucursales: lectura", "Consulta de sucursales.", False),
    "branches:write": ("Sucursales: escritura", "Administración de sucursales.", True),
    "vehicles:read": ("Vehículos: lectura", "Consulta del inventario vehicular.", False),
    "vehicles:write": ("Vehículos: escritura", "Administración vehicular.", True),
    "customers:read": ("Clientes: lectura", "Consulta de clientes autorizados.", True),
    "customers:write": ("Clientes: escritura", "Administración de clientes.", True),
    "inventory:read": ("Inventario: lectura", "Consulta de artículos y stock.", False),
    "inventory:write": ("Inventario: escritura", "Movimientos y administración de stock.", True),
    "sales:read": ("Ventas: lectura", "Consulta de cotizaciones, reservas y ventas.", True),
    "sales:write": ("Ventas: escritura", "Operación de ventas.", True),
    "invoices:read": ("Facturación: lectura", "Consulta de comprobantes.", True),
    "invoices:write": ("Facturación: escritura", "Operación de facturación.", True),
    "documents:read": ("Documentos: lectura", "Consulta de metadatos documentales autorizados.", True),
    "documents:write": ("Documentos: escritura", "Gestión documental.", True),
    "notifications:read": ("Notificaciones: lectura", "Consulta de notificaciones.", True),
    "notifications:write": ("Notificaciones: escritura", "Envío y administración de notificaciones.", True),
    "reports:read": ("Reportes: lectura", "Consulta de reportes.", True),
    "imports:read": ("Importaciones: lectura", "Consulta de lotes de importación.", True),
    "imports:write": ("Importaciones: escritura", "Gestión de importaciones.", True),
    "enterprise:read": ("Empresa avanzada: lectura", "Consulta de configuración empresarial.", True),
    "enterprise:write": ("Empresa avanzada: escritura", "Gestión de configuración empresarial.", True),
    "sri:read": ("SRI: lectura", "Consulta de configuración tributaria preparada.", True),
    "sri:write": ("SRI: escritura", "Gestión de configuración tributaria preparada.", True),
    "audit:read": ("Auditoría: lectura", "Consulta de trazabilidad y alertas.", True),
    "security:read": ("Seguridad: lectura", "Consulta de políticas y sesiones.", True),
    "security:write": ("Seguridad: escritura", "Administración de seguridad.", True),
    "continuity:read": ("Continuidad: lectura", "Consulta de backups y simulacros.", True),
    "continuity:write": ("Continuidad: escritura", "Operación de continuidad.", True),
    "privacy:read": ("Privacidad: lectura", "Consulta de procesos de privacidad.", True),
    "privacy:write": ("Privacidad: escritura", "Gestión de privacidad.", True),
    "leads:read": ("Leads: lectura", "Consulta de CRM.", True),
    "leads:write": ("Leads: escritura", "Creación y gestión de leads.", True),
    "analytics:read": ("Analítica: lectura", "Consulta de analítica comercial.", True),
    "integrations:read": ("Integraciones: lectura", "Consulta de logs y webhooks.", True),
    "integrations:manage": ("Integraciones: administración", "Gestión de clientes API y webhooks.", True),
    "bi:read": ("BI: lectura", "Datasets estables para Power BI u otras herramientas.", True),
    "accounting:export": ("Contabilidad: exportación", "Exportación contable autorizada.", True),
}


class Command(BaseCommand):
    help = "Crea o actualiza los alcances API de Vinova Pro."

    def handle(self, *args, **options):
        for code, (name, description, sensitive) in SCOPES.items():
            APIScope.objects.update_or_create(
                code=code,
                defaults={"name": name, "description": description, "is_sensitive": sensitive, "is_active": True},
            )
        self.stdout.write(self.style.SUCCESS(f"{len(SCOPES)} alcances API disponibles."))
