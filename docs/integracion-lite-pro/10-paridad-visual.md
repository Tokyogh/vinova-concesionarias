# 10 — Paridad visual LITE → PRO

Fecha: 2026-10-12. Estado: **paridad estructural validada; aprobación visual humana y proveedores externos pendientes**.

## Método reproducible

1. LITE se ejecutó en `127.0.0.1:5001` contra una copia temporal y anonimizada de su SQLite. El archivo original no se modificó.
2. PRO se ejecutó en el contenedor local de revisión, sin tocar producción.
3. `scripts/ui/portal_parity.py` autenticó cuentas QA desde variables de entorno; no escribe ni imprime credenciales.
4. Se capturaron las diez áreas de ambos productos en `1440×900`, `768×1024` y `390×844`: **60 capturas**, más geometría DOM, overlays y mapas de diferencia.
5. Los artefactos regenerables certificados están en `run/portal-parity/certified/` y permanecen fuera de Git.

El navegador integrado de revisión no estaba disponible en la sesión. La validación visual se realizó con Chromium mediante Playwright local; esto no cambia las páginas ni los datos examinados.

## Resultado geométrico

| Viewport | Referencia LITE | PRO final | Resultado |
|---|---|---|---|
| 1440×900 | sidebar `260×900`, sticky, padding `25px` | sidebar `260×900`, sticky, padding `25px` | COINCIDE |
| 768×1024 | sidebar de ancho completo antes del contenido | sidebar `768×760`, relativo, antes del contenido | COINCIDE en patrón; menor altura por agrupación tipográfica |
| 390×844 | sidebar `390px`, relativo, antes del contenido | sidebar `390×760`, relativo, antes del contenido | COINCIDE en patrón; menor altura por espaciado modular |
| Todos | sin overflow horizontal | **0/30 pantallas PRO con overflow** | COINCIDE |

Altura inicial de escritorio: LITE `1106px`, PRO `1165px` (diferencia `+59px`). En las demás áreas la altura responde al contenido real: PRO conserva controles empresariales adicionales de seguridad, documentos y perfil, y LITE conserva datos históricos propios de su copia QA.

## Comparación por área

| Área | Estructura LITE restaurada en PRO | Diferencia restante | Severidad | Estado |
|---|---|---|---|---|
| Inicio | Shell lateral, topbar, 4 métricas, cuadrícula 2×2, garaje, próximos servicios, gráfica y actividad | Los valores dependen de expedientes QA distintos | Informativa | COMPLETO |
| Mis vehículos | Tarjetas/galería, búsqueda y acceso al detalle | PRO conserva paginación server-side | Informativa | COMPLETO |
| Agregar vehículo | Tarjeta/formulario VNV y kilometraje | Validación PRO es más estricta | Informativa | SUPERADO |
| Historial | Lista privada por vehículo y estado | PRO muestra número de orden y transiciones auditadas | Informativa | SUPERADO |
| Próximos servicios | Vista separada, fecha/km y estado | Sin scheduler automático por exclusión explícita | Fuera de alcance | COMPLETO |
| Manuales | Biblioteca por modelo/año y descargas | PRO añade documentos privados en la misma área | Informativa | SUPERADO |
| Facturas | Lista, estado, fecha, total y detalle | PRO añade tipo/moneda/pagos | Informativa | SUPERADO |
| Perfil | Identidad, contacto y avatar | PRO bloquea identidad y añade campos de contacto auditados | Seguridad | SUPERADO |
| Notificaciones | Bandeja, lectura, bulk, archivo y preferencias | “Ocultar” LITE se representa como archivo auditable | Informativa | COMPLETO |
| Configuración | Preferencias y salida | PRO añade contraseña, 2FA, sesiones y privacidad | Seguridad | SUPERADO |
| Modal vehículo | Apertura progresiva desde dashboard/garaje y cuatro pestañas | Sin JS degrada a página privada completa | Accesibilidad | COMPLETO |

## Diferencias de píxel

El arnés genera `overlay-*` y `diff-*` para inspección. El error RGB medio no se usa como umbral de aceptación porque la solicitud autoriza cambiar la paleta y los datasets no son idénticos. Sus promedios fueron 72,83% (escritorio), 52,37% (tablet) y 56,28% (móvil); la mayor parte corresponde al tema oscuro LITE frente a superficies/tokens PRO y a contenido QA distinto.

Los criterios útiles —geometría del shell, orden de áreas, jerarquía de tarjetas, ausencia de overflow, rutas, estados, acciones y responsive— sí se evaluaron independientemente del color.

## Correcciones derivadas de la comparación

- Se sustituyó la navegación superior PRO por el shell lateral de 260 px.
- Se restauró el orden de diez áreas y la separación Historial/Próximos servicios.
- Se recuperó el resumen de cuatro tarjetas y la cuadrícula principal 2×2.
- Se añadió la serie de servicios completados de seis meses.
- Se añadió el detalle progresivo del vehículo con Resumen, Historial, Mantenimiento y Documentación.
- Se alineó el patrón responsive de LITE: sidebar de ancho completo antes del contenido en tablet/móvil.
- Se corrigió el único falso positivo de overflow: el arnés apuntaba a una URL de canje inexistente y capturaba el 404 de depuración.
- Chromium detectó contraste 4,01:1 en el texto auxiliar de métricas; el token se elevó a 4,5:1 o más y el E2E completo volvió a pasar.

## Desviaciones intencionales

1. Colores, tipografía base y tokens pertenecen a PRO, según la autorización expresa.
2. PRO mantiene información y controles empresariales adicionales; no se ocultaron 2FA, sesiones, privacidad, estados ni auditoría para igualar una pantalla más corta.
3. Las acciones siguen siendo rutas Django profundas y accesibles. El modal es mejora progresiva, no una segunda fuente de datos.
4. Con `post_sales` deshabilitado se ocultan las dos entradas de servicio y sus rutas devuelven 404 contractual; el resto del portal sigue operativo.
5. No se copió código, SQL, credenciales, archivos privados ni assets externos de LITE.

## Gate pendiente

No se declara igualdad píxel a píxel ni aprobación humana final. La paridad estructural/funcional automatizable está cubierta; la aprobación visual manual en staging continúa como gate externo de producción.
