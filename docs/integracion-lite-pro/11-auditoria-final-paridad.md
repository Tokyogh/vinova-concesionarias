# 11 — Auditoría final de paridad y production readiness

Fecha: 2026-10-12  
Rama: `integration/lite-pro`  
Base preservada: `569b979`  
Veredicto: **certificación local aprobada; no se declara production-ready hasta cerrar gates externos**.

## Alcance certificado

- Auditoría LITE → PRO de 68 reglas Flask / 66 endpoints.
- Auditoría PRO → LITE de permisos, ownership, capacidades añadidas y degradación por módulos.
- Diez áreas del portal cliente: Inicio, Mis vehículos, Agregar vehículo, Historial, Próximos servicios, Manuales, Facturas, Perfil, Notificaciones y Configuración.
- Shell, tarjetas, cuadrículas, modal, cuatro pestañas, estados vacíos, búsqueda, filtros, formularios y responsive.
- No se modificó `web_carros/`; LITE se ejecutó contra una copia temporal anonimizada de su base.
- No se alteró producción ni se realizó merge o despliegue.

## Causa de la divergencia y solución

PRO ya poseía equivalentes seguros para las funciones útiles de LITE, pero el portal se había reinterpretado como páginas con navegación superior. Eso eliminaba la distribución visual y varias interacciones de `profile.html` aunque el backend estuviera completo.

La corrección conserva los modelos y servicios PRO y restaura la experiencia de LITE:

- sidebar de 260 px, topbar y orden de áreas;
- cuatro métricas y cuadrícula principal 2×2;
- serie de servicios completados de seis meses;
- separación Historial/Próximos servicios;
- detalle progresivo de vehículo con Resumen, Historial, Mantenimiento y Documentación;
- fallback a página completa cuando no hay JavaScript;
- patrón responsive de sidebar de ancho completo antes del contenido;
- rutas, CSRF, permisos, auditoría y ownership de PRO sin atajos por correo, cédula o nombre.

## Auditoría bidireccional

### LITE → PRO

Las 68 reglas están mapeadas individualmente en `09-paridad-funcional.md`. El portal privado queda completo o superado. Permanecen dos diferencias públicas P3 ya declaradas: catálogo público de repuestos y directorio/mapa ampliado de sedes. No bloquean el portal privado.

### PRO → LITE

| Control/capacidad PRO | Resultado |
|---|---|
| `Customer.account` activo/VIP + `portal.access` vigente | Preservado |
| Staff sin rol cliente | Sigue denegado; no recibe acceso implícito |
| Dos clientes diferentes | Selectors y detalles devuelven solo recursos propios; ajenos resultan 404 |
| Vínculo de vehículo inactivo/transferido | No expone unidad ni historial anterior |
| Documentos, facturas y notificaciones | Ownership se resuelve en selectors existentes |
| Canje VNV | Conserva servicio atómico, unicidad e idempotencia |
| Módulo `post_sales` apagado | Oculta navegación, pestañas y consultas; rutas directas devuelven 404 |
| Identidad del cliente | Permanece no editable en el portal |
| PDF/archivos privados | Descarga autenticada, auditada y `no-store` |
| 2FA, sesiones, privacidad y preferencias | Se conservan como capacidades superiores de PRO |

La auditoría inversa detectó y corrigió que el modal inicialmente preparaba datos de servicios aun con `post_sales` apagado. Ahora el gate se aplica a navegación, pestañas, consultas y rutas.

## Evidencia visual

- 60 capturas finales y 30 pares overlay/diff.
- Viewports: 1440×900, 768×1024 y 390×844.
- 30/30 pantallas PRO sin overflow horizontal.
- Sidebar de escritorio: LITE y PRO `260×900`, sticky, padding `25px`.
- El único falso overflow observado correspondía a una URL incorrecta del arnés que capturaba un 404; la ruta y la evidencia se corrigieron.
- La diferencia de píxel no es gate porque paleta y datasets son distintos por diseño. El detalle está en `10-paridad-visual.md`.

## Resultados de certificación

| Gate | Resultado |
|---|---|
| Ruff, repositorio completo | PASS |
| `manage.py check` | PASS, 0 issues |
| `makemigrations --check --dry-run` | PASS, sin cambios |
| `migrate --check` | PASS, sin migraciones pendientes |
| Motor de datos local | PostgreSQL confirmado |
| Dependencias instaladas (`pip check`) | PASS, sin requisitos rotos |
| Suite completa | **2432 passed, 39 skipped** |
| Suite portal aislada | **51 passed, 2 skipped** |
| Regresiones finales shell/servicios | **33 passed** |
| E2E portal Chromium | **1 passed** |
| E2E completo Chromium | **32 passed, 0 failed, 0 skipped** |
| Responsive/accesibilidad E2E | 7/7 PASS |
| Production settings `check --deploy` con configuración segura sintética | PASS, 0 issues |
| Captura visual certificada | 60/60, 0 fallos; 0 overflow |

Los 39 skips de la corrida Pytest general incluyen los E2E que, por diseño, solo se habilitan en su runner dedicado. El runner dedicado los ejecutó después y cerró 32/32 en Chromium sobre PostgreSQL y Redis temporales.

## Hallazgos corregidos durante la certificación

1. Cliente heredado con asociación válida pero no resuelta: corregido previamente en `569b979`.
2. Shell PRO visualmente divergente: restaurado.
3. Historial y próximos servicios no separados visualmente: restaurados mediante vistas filtradas.
4. Falta de modal/pestañas equivalentes: restaurada con mejora progresiva.
5. Contraste auxiliar 4,01:1 detectado por Chromium: corregido a token con ratio ≥4,5:1.
6. Preparación de datos postventa con el módulo apagado: eliminada.
7. URL incorrecta del arnés visual: corregida; ya no produce 404/overflow falso.

## Gates externos abiertos

Por instrucción, estos puntos impiden afirmar “production-ready” aunque la certificación local sea satisfactoria:

- aprobación visual humana en staging con datos representativos;
- ciclo real de Cloudinary/storage externo y correo en staging;
- secretos, dominios HTTPS, proxy y certificados reales del entorno objetivo;
- escaneo Trivy HIGH/CRITICAL: la herramienta no está instalada en este host;
- validación operativa de backup/restore, observabilidad y dependencias externas del despliegue;
- las dos mejoras públicas P3 (repuestos y mapa de sedes) si producto decide incluirlas en el release.

SRI, SaaS/multi-tenant y recordatorios automáticos continúan excluidos expresamente y no son defectos de esta integración.

## Veredicto

La integración alcanza **paridad estructural y funcional local del portal cliente**, con controles PRO preservados y pruebas de regresión satisfactorias. No se afirma igualdad cromática/píxel a píxel ni readiness de producción hasta cerrar los gates externos anteriores. La rama puede enviarse a revisión y staging; no se autoriza merge ni despliegue desde este cierre.
