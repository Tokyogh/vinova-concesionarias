# Manual del administrador general

Empresa, sucursales, usuarios, roles, configuración y supervisión del sistema.

- Tipo: `manual`
- Categoría: `administracion`
- Permiso requerido: `accounts.manage_users`
- Roles específicos: `superadmin, admin_general`
- Ruta contextual: `accounts:user_list`

Manual del administrador general

Objetivo
Administrar la instalación empresarial manteniendo mínimo privilegio, trazabilidad y continuidad operativa.

Procedimiento recomendado
1. Verifica primero el perfil empresarial, datos de contacto y sucursales.
2. Crea cuentas individuales para cada colaborador.
3. Asigna únicamente los roles necesarios y, cuando corresponda, una sucursal.
4. Revisa que los usuarios administrativos tengan 2FA habilitado.
5. Configura políticas de aprobación, correo, backups e integraciones de forma gradual.
6. Consulta auditoría y alertas antes de cerrar una incidencia.
7. Realiza una copia de seguridad antes de actualizaciones importantes.

Controles importantes
• No reutilices usuarios genéricos entre personas.
• No cambies SECRET_KEY ni VINOVA_API_TOKEN_PEPPER sin un procedimiento de rotación.
• No uses docker compose down -v salvo que quieras eliminar deliberadamente los volúmenes.

Antes de terminar
□ Roles revisados.
□ Sucursales activas y correctas.
□ Backups verificados.
□ Alertas críticas atendidas.
