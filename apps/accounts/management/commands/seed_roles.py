"""ES: Implementa el comando administrativo «seed roles» para cuentas.

EN: Implements the «seed roles» management command for accounts.

Contexto existente / Existing context:
Django management command for seed roles.
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from apps.accounts.models import PermissionCode, Role

ROLE_DEFINITIONS = {
    'superadmin': ('Superadmin del sistema', 1), 'admin_general': ('Administrador general', 5),
    'admin_sucursal': ('Administrador de sucursal', 10), 'gerente_comercial': ('Gerente comercial', 15),
    'jefe_inventario': ('Jefe de inventario', 20), 'vendedor': ('Vendedor', 30),
    'asesor_postventa': ('Asesor de postventa', 35), 'facturacion': ('Facturación', 35),
    'bodega': ('Bodega / stock', 40), 'marketing': ('Marketing / catálogo', 45),
    'soporte_cliente': ('Atención al cliente', 50), 'auditor': ('Auditor / solo lectura', 80),
    'cliente': ('Cliente', 100),
}
PERMISSIONS = [
    ('dashboard', 'dashboard.view', 'Ver dashboard'), ('accounts', 'accounts.manage_users', 'Gestionar usuarios'),
    ('accounts', 'accounts.assign_roles', 'Asignar roles'), ('companies', 'companies.manage', 'Gestionar empresa'),
    ('branches', 'branches.manage', 'Gestionar sucursales'), ('vehicles', 'vehicles.view', 'Ver vehículos'),
    ('vehicles', 'vehicles.manage', 'Gestionar vehículos'), ('vehicles', 'vehicles.publish', 'Publicar u ocultar vehículos'),
    ('vehicles', 'vehicles.link_codes', 'Generar y revocar códigos de vinculación'),
    ('vehicles', 'vehicles.delete_permanent', 'Eliminar vehículos permanentemente'), ('inventory', 'inventory.view', 'Ver inventario'),
    ('inventory', 'inventory.manage_stock', 'Gestionar stock'), ('customers', 'customers.view', 'Ver clientes'),
    ('customers', 'customers.manage', 'Gestionar clientes'), ('sales', 'sales.quote', 'Crear cotizaciones'),
    ('sales', 'sales.reserve', 'Crear reservas'), ('sales', 'sales.sell', 'Registrar ventas'),
    ('invoices', 'invoices.view', 'Ver facturación'), ('invoices', 'invoices.issue', 'Emitir facturas'), ('invoices', 'invoices.manage', 'Gestionar facturación'), ('invoices', 'invoices.void', 'Anular comprobantes'), ('documents', 'documents.view', 'Ver biblioteca documental'),
    ('documents', 'documents.manage', 'Gestionar documentos y recursos'), ('documents', 'documents.download_private', 'Descargar documentos privados'),
    ('notifications', 'notifications.view', 'Ver notificaciones'), ('notifications', 'notifications.send', 'Enviar notificaciones'), ('notifications', 'notifications.manage_templates', 'Gestionar plantillas de notificación'), ('reports', 'reports.view', 'Ver reportes'), ('imports', 'imports.manage', 'Gestionar importaciones masivas'), ('data', 'data.export', 'Exportar datasets y datos operativos'), ('enterprise', 'enterprise.manage', 'Gestionar centro empresarial'), ('sri', 'sri.manage', 'Gestionar configuración SRI'), ('approvals', 'approvals.manage', 'Gestionar políticas de aprobación'), ('audit', 'audit.view', 'Ver auditoría'), ('audit', 'audit.export', 'Exportar auditoría'), ('audit', 'audit.manage_alerts', 'Gestionar alertas de seguridad'),
    ('campaigns', 'campaigns.view', 'Ver campanas'), ('campaigns', 'campaigns.manage', 'Preparar y segmentar campanas'),
    ('campaigns', 'campaigns.send', 'Confirmar campanas'),
    ('leads', 'leads.view', 'Ver CRM y leads'), ('leads', 'leads.manage', 'Gestionar CRM y leads'),
    ('leads', 'leads.assign', 'Asignar leads a sucursales y asesores'), ('leads', 'leads.export', 'Exportar leads'),
    ('analytics', 'analytics.view', 'Ver analítica comercial'), ('analytics', 'analytics.export', 'Exportar datasets comerciales y BI'),
    ('continuity', 'continuity.view', 'Ver continuidad y backups'), ('continuity', 'continuity.manage', 'Ejecutar y verificar backups'),
    ('continuity', 'continuity.restore', 'Preparar y registrar restauraciones'),
    ('privacy', 'privacy.view', 'Ver protección de datos'), ('privacy', 'privacy.manage', 'Gestionar solicitudes y retención'),
    ('privacy', 'privacy.export', 'Exportar datos personales'), ('privacy', 'privacy.anonymize', 'Anonimizar datos personales'),
    ('security', 'security.view', 'Ver centro de seguridad'), ('security', 'security.manage', 'Gestionar políticas y 2FA'),
    ('security', 'security.approve_staff_access', 'Aprobar acceso Staff excepcional'),
    ('integrations', 'integrations.view', 'Ver API, integraciones y BI'), ('integrations', 'integrations.manage', 'Gestionar clientes API y webhooks'),
    ('help', 'help.view', 'Ver centro de ayuda y capacitación'), ('help', 'help.manage', 'Gestionar contenido de ayuda'),
    ('quality', 'quality.view', 'Ver historial y resultados del QA Bot'), ('quality', 'quality.run', 'Ejecutar perfiles cerrados del QA Bot'),
    ('post_sales', 'post_sales.view', 'Ver postventa'), ('post_sales', 'post_sales.manage', 'Gestionar órdenes de postventa'),
    ('portal', 'portal.access', 'Acceso al portal del cliente'),
]
ROLE_PERMISSION_MAP = {
    'admin_general': [p[1] for p in PERMISSIONS],
    'admin_sucursal': ['dashboard.view','vehicles.view','vehicles.manage','vehicles.link_codes','inventory.view','inventory.manage_stock','customers.view','customers.manage','sales.quote','sales.reserve','sales.sell','invoices.view','invoices.issue','documents.view','documents.manage','documents.download_private','notifications.view','notifications.send','notifications.manage_templates','campaigns.view','campaigns.manage','campaigns.send','reports.view','imports.manage','data.export','leads.view','leads.manage','leads.assign','leads.export','analytics.view','analytics.export','privacy.view','privacy.manage','privacy.export'],
    'gerente_comercial': ['dashboard.view','vehicles.view','customers.view','sales.quote','sales.reserve','sales.sell','invoices.view','documents.view','documents.download_private','notifications.view','notifications.send','campaigns.view','campaigns.manage','campaigns.send','reports.view','leads.view','leads.manage','leads.assign','leads.export','analytics.view','analytics.export'],
    'jefe_inventario': ['dashboard.view','vehicles.view','vehicles.manage','inventory.view','inventory.manage_stock','reports.view','imports.manage','data.export'],
    'vendedor': ['dashboard.view','vehicles.view','customers.view','customers.manage','sales.quote','sales.reserve','documents.view','notifications.view','notifications.send','leads.view','leads.manage'],
    'asesor_postventa': ['dashboard.view','customers.view','vehicles.link_codes','documents.view','documents.download_private','notifications.view','notifications.send','post_sales.view','post_sales.manage'],
    'facturacion': ['dashboard.view','sales.sell','invoices.view','invoices.issue','invoices.manage','invoices.void','documents.view','documents.manage','documents.download_private','notifications.view','notifications.send'],
    'bodega': ['dashboard.view','inventory.view','inventory.manage_stock'], 'marketing': ['dashboard.view','vehicles.view','vehicles.manage','vehicles.publish','customers.view','notifications.view','notifications.send','notifications.manage_templates','campaigns.view','campaigns.manage','campaigns.send','imports.manage','analytics.view'],
    'soporte_cliente': ['dashboard.view','customers.view','documents.view','notifications.view','notifications.send','leads.view','leads.manage','privacy.view','privacy.manage'], 'auditor': ['dashboard.view','vehicles.view','inventory.view','customers.view','sales.quote','invoices.view','documents.view','notifications.view','reports.view','data.export','audit.view','audit.export','leads.view','leads.export','analytics.view','analytics.export','continuity.view','privacy.view','privacy.export','security.view','integrations.view','quality.view'],
    'cliente': ['portal.access'],
}

for _role_code, _permissions in ROLE_PERMISSION_MAP.items():
    if _role_code != 'cliente' and 'help.view' not in _permissions:
        _permissions.append('help.view')


class Command(BaseCommand):
    help = 'Crea roles y permisos base de Vinova Pro.'
    @transaction.atomic
    def handle(self, *args, **options):
        perms = {}
        for module, code, name in PERMISSIONS:
            perms[code], _ = PermissionCode.objects.update_or_create(code=code, defaults={'module': module, 'name': name})
        for code, (name, level) in ROLE_DEFINITIONS.items():
            role, _ = Role.objects.update_or_create(code=code, defaults={'name': name, 'level': level, 'role_type': Role.RoleType.SYSTEM})
            role.permissions.set(perms.values() if code == 'superadmin' else [perms[p] for p in ROLE_PERMISSION_MAP.get(code, [])])
        self.stdout.write(self.style.SUCCESS('Roles y permisos base creados.'))
