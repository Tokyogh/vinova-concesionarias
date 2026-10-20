# Paridad VINOVA LITE → PRO

`web_carros/` es la referencia LITE de solo lectura. PRO replica el portal
cliente y reemplaza lógica insegura/obsoleta por servicios, modelos, permisos,
ownership y auditoría empresariales.

## Resultado

- portal privado, garaje, documentos, facturas, notificaciones e instituciones:
  paridad principal verificada;
- PRO mejora permisos, privacidad, archivos y transacciones;
- códigos revocados no se reactivan: se emite uno nuevo, decisión intencional;
- coordenadas no se inventan: una sede incompleta conserva lista/fallback;
- foto y website específicos por sede: integrados con validación y fallback;
- catálogo público de repuestos: integrado sobre inventario PRO, sin exponer cantidades, costos ni movimientos;
- tecnologías opcionales del mapa y analítica: bloqueadas hasta consentimiento, mejora deliberada frente a LITE;
- SRI, recordatorios e importación histórica: exclusiones expresas.

La paridad de sedes y repuestos quedó demostrada localmente en F2. La carga real
de multimedia, MapTiler restringido por dominio y la aprobación visual humana
siguen siendo gates externos, no brechas funcionales del código.

Matriz ruta por ruta: [B2](auditoria-integral/02-paridad-lite-pro.md). Las
decisiones visuales y capturas históricas permanecen en `ui/`,
`integracion-lite-pro/` y `vinova-redesign/`.
