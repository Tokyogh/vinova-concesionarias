# Documentación de VINOVA PRO 2.0.0

Índice canónico de la distribución comercial. La documentación se organiza por
producto, operación, seguridad y pruebas; los informes internos de coordinación
no forman parte de esta distribución.

## Producto y arquitectura

- [Estado actual, límites y gates](ESTADO_ACTUAL.md)
- [Funcionalidades](FUNCIONALIDADES.md)
- [Arquitectura](ARQUITECTURA.md)
- [Base de datos](BASE_DATOS.md)
- [Módulos y feature flags](MODULOS.md)
- [Roles y permisos](ROLES_PERMISOS.md)
- [Paridad VINOVA LITE → PRO](PARIDAD_LITE_PRO.md)
- [Changelog](CHANGELOG.md)

## Instalación, configuración y desarrollo

- [Instalación](INSTALACION.md)
- [Configuración](CONFIGURACION.md)
- [API e integraciones](API.md)
- [Power BI](POWER_BI.md)
- [Testing y calidad](TESTING.md)
- [Dependencias frontend](DEPENDENCIAS_FRONTEND.md)
- [Mapas funcionales](mapas-funcionales/README.md)

## Seguridad y privacidad

- [Guía técnica de seguridad](SECURITY.md)
- [Auditoría de ciberseguridad](auditoria-integral/05-ciberseguridad.md)
- [Matriz RBAC](auditoria-integral/04-matriz-rbac.md)
- [Modelo de amenazas CIA/STRIDE](seguridad-avanzada/03-modelo-amenazas.md)
- [Matriz OWASP ASVS 5.0](seguridad-avanzada/04-matriz-asvs.md)
- [Validación contextual](seguridad-avanzada/05-validacion-contextual.md)
- [Hardening y SSRF](seguridad-avanzada/06-hardening-aplicacion.md)
- [Cookies y sesiones](seguridad-avanzada/07-cookies-sesiones.md)
- [Acceso Staff adaptativo](seguridad-avanzada/08-acceso-staff-adaptativo.md)
- [Consentimiento de tecnologías opcionales](seguridad-avanzada/09-consentimiento-cookies.md)
- [Privacidad y documentos legales](seguridad-avanzada/10-privacidad-documentos-legales.md)
- [Procedimientos de privacidad](seguridad-avanzada/10-procedimientos-privacidad.md)
- [Registro preliminar de tratamientos](seguridad-avanzada/10-registro-tratamientos.md)
- [Cadena de suministro](seguridad-avanzada/11-cadena-suministro.md)
- [Disponibilidad y archivos](seguridad-avanzada/12-disponibilidad-archivos.md)
- [Escaneo Trivy](SECURITY_SCANNING_TRIVY.md)

## Operación y despliegue

- [Producción](PRODUCCION.md)
- [Operación diaria](OPERACION.md)
- [Actualización](ACTUALIZACION.md)
- [Arquitectura segura de actualizaciones](UPDATE_ARCHITECTURE.md)
- [Lifecycle](LIFECYCLE.md)
- [Backups](BACKUPS.md)
- [Recuperación de emergencia](EMERGENCY_RECOVERY.md)
- [Transfer de instalaciones](TRANSFER.md)
- [Deployment Smoke Bot](DEPLOYMENT_SMOKE_BOT.md)
- [Matriz smoke de roles](DEPLOYMENT_SMOKE_ROLE_MATRIX.md)
- [CI/CD del smoke](CI_CD_DEPLOYMENT_SMOKE.md)

## Manuales y testeo beta

- [Índice de manuales](manuals/README.md)
- [Primeros pasos](manuals/primeros-pasos-vinova-pro.md)
- [Índice maestro de testeo beta](testeo-beta/testeo-indice-maestro.md)
- [Matriz de trazabilidad](testeo-beta/testeo-matriz-trazabilidad.md)
- [Plantilla individual de ejecución](testeo-beta/testeo-plantilla-ejecucion.md)
- [Plantilla de incidencias](testeo-beta/testeo-plantilla-incidencia.md)
- [Consolidación de resultados](testeo-beta/testeo-consolidacion-resultados.md)

## Referencias técnicas conservadas

- `auditoria-integral/01-05`: inventario funcional, flujos, RBAC y seguridad.
- `vinova-redesign/`: mapas de datos, matriz funcional e integraciones útiles
  para mantenimiento; un reporte histórico no UTF-8 se conserva sin modificar.
- `ui/`: especificaciones, geometría y recursos de referencia visual.
- `QA_FULL_V200.md` y `UI_UX_V200.md`: evidencia técnica y criterios de interfaz.

Los resultados históricos de pruebas no sustituyen una ejecución sobre el
commit candidato. Los textos de privacidad y licenciamiento requieren revisión
jurídica antes de su adopción definitiva.
