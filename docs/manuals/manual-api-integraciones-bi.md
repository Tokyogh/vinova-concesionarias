# Manual de API, webhooks y BI

Clientes API, alcances, tokens, idempotencia, webhooks y datasets estables.

- Tipo: `manual`
- Categoría: `integraciones`
- Permiso requerido: `integrations.view`
- Roles específicos: `según permisos`
- Ruta contextual: `api_internal:dashboard`

Manual de API, webhooks y BI

Objetivo
Conectar sistemas externos con credenciales de mínimo privilegio y trazabilidad completa.

Procedimiento recomendado
1. Crea un usuario de servicio con permisos mínimos.
2. Crea el cliente API, limita sucursal, IP/CIDR, vencimiento y rate.
3. Selecciona solo los alcances requeridos.
4. Guarda el token mostrado una sola vez en un gestor de secretos.
5. Usa Idempotency-Key en operaciones externas que lo requieran.
6. Configura webhooks HTTPS y conserva el secreto de firma.
7. Revisa entregas, reintentos y logs sin guardar cuerpos sensibles.
8. Usa datasets BI versionados y protege los archivos exportados.

Controles importantes
• Un alcance API no sustituye el permiso del usuario de servicio.
• No uses redes privadas como destino de webhook en producción.
• Rotar el pepper invalida todos los tokens.

Antes de terminar
□ Usuario de servicio revisado.
□ Token almacenado de forma segura.
□ Webhook de prueba correcto.
□ Logs sin secretos.
