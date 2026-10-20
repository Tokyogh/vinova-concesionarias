# F6 — Hardening reproducible de aplicación

Fecha: 2026-10-16

## Alcance corregido

### Webhooks y SSRF

- La URL se valida y resuelve una sola vez antes del envío.
- Se rechaza la respuesta DNS completa si contiene cualquier dirección no global, salvo la excepción explícita para redes privadas.
- El transporte conecta a la IP aprobada y conserva el nombre original para `Host`, SNI y validación del certificado TLS.
- No utiliza proxy ni sigue redirecciones; una URL distinta después de validar se rechaza antes de abrir la conexión.
- Los fragmentos de respuesta almacenados pasan por redacción de datos sensibles.

Esto cierra el cambio de resolución entre validación y conexión. No sustituye controles de egreso de red en infraestructura.

### Autenticación y contraseñas

- El reto 2FA limita intentos por IP y por combinación IP/cuenta, devuelve `429` con `Retry-After` y audita la denegación.
- Un código correcto limpia sus contadores fallidos.
- La política inicial favorece longitud y frases únicas sin exigir composición arbitraria ni rotación periódica.
- La migración modifica únicamente registros que conservan simultáneamente todos los valores iniciales anteriores; las políticas personalizadas quedan intactas.
- La exigencia global de MFA no se activa todavía: se integrará con recuperación y acceso Staff adaptativo en F8 para evitar bloqueo operativo.

### CSP y estilos de marca

- Cada respuesta recibe un nonce criptográfico y todos los bloques `<style>` propios lo utilizan.
- `style-src` deja de admitir `unsafe-inline`.
- Los colores configurables aceptan exclusivamente `#RRGGBB` en modelo, formularios y API; los valores heredados inválidos se sustituyen de forma segura al renderizar.
- `style-src-attr 'unsafe-inline'` permanece acotado a cinco atributos de dimensión calculados por servidor. Su eliminación completa requiere moverlos a clases o variables generadas sin perder las gráficas actuales.

## Controles previamente verificados y no duplicados

La auditoría B12 y sus regresiones mantienen evidencia sobre ORM/parametrización, CSRF, ownership/IDOR, RBAC, alcance por sucursal, redirects, path traversal, uploads privados, transacciones financieras, módulos ON/OFF, CORS, headers, sesiones, redacción de logs y copias de continuidad. F6 añadió cobertura solo donde se reprodujo una brecha concreta.

## Evidencia automatizada

- `apps/api/tests/test_webhook_ssrf.py`: respuestas DNS mixtas, destino fijado, SNI/certificado y mutación de URL.
- `apps/security_center/tests/test_security_center.py`: límite 2FA, limpieza de contadores y valores iniciales de contraseña.
- `tests/security/test_d5_defensive_controls.py`: nonce CSP y eliminación de `unsafe-inline` en bloques de estilo.
- `apps/common/tests/test_domain_input_validation.py`: aceptación, rechazo y fallback de colores.
- Regresión amplia afectada: 1.921 pruebas aprobadas y 1 omisión declarada.
- Django check, drift de migraciones, Ruff global, compileall y diff-check: aprobados.
- Migraciones de sedes, colores y política de contraseña: aplicadas en PostgreSQL local Docker.

## Riesgos y dependencias pendientes

- Antivirus/CDR de archivos externos: F12 confirmó la ausencia; requiere proveedor o servicio desplegable y cuarentena antes de producción.
- Vault/HSM, filtrado de egreso y sink inmutable: controles de infraestructura no verificables localmente.
- CSP de atributos de estilo: excepción residual descrita y limitada; pendiente de refactor visual específico.
- MFA obligatorio para Staff: pendiente de F8 junto con recuperación y acceso excepcional probado.
- DNS/TLS reales, certificados y webhooks de proveedores: pendientes de staging candidato.

No se declara seguridad absoluta ni cumplimiento ASVS global por este bloque.
