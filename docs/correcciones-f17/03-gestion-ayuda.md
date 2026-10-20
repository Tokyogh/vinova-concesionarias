# F17.8 — Gestión versionada de ayuda

Fecha: 2026-10-18

## Alcance implementado

El contenido de ayuda puede gestionarse desde VINOVA PRO sin editar código ni ejecutar un despliegue. La interfaz permite listar, crear, editar, previsualizar, publicar, despublicar, consultar el historial y restaurar una versión anterior. La restauración no borra historia: crea una versión nueva con la instantánea elegida.

No se incorporó borrado destructivo de artículos. La despublicación conserva el contenido, las relaciones y la trazabilidad.

## Autorización e integridad

- Todas las rutas de gestión exigen el permiso efectivo `help.manage`; `is_staff` por sí solo no concede acceso.
- Los lectores siguen viendo únicamente artículos publicados que cumplen sus permisos y roles.
- Categoría, permiso, roles y nombre de ruta se validan contra configuración existente.
- Cada escritura usa servicios transaccionales y bloqueo de fila cuando modifica un artículo existente.
- Crear, editar, publicar, despublicar y restaurar generan eventos de auditoría.
- La combinación artículo-versión es única en base de datos.
- La migración crea la versión 1 de los artículos preexistentes, sin cambiar su estado publicado ni su contenido.

## Tratamiento del contenido

El contenido se almacena como texto y se renderiza con escape automático. Una etiqueta como `<script>` se muestra literalmente y no se ejecuta. Esto evita introducir un editor HTML confiable sin una política de sanitización aprobada.

## Evidencia

- 16 pruebas de `apps.help_center.tests` aprobadas.
- Cobertura F17: denegación sin `help.manage`, creación y auditoría, escape de contenido, ocultamiento de borradores, edición, publicación, despublicación, historial, restauración y ayuda contextual disponible sin despliegue.
- Django check y comprobación de drift de migraciones aprobados.
- Ruff y compileall aprobados tras corregir el único import no utilizado detectado.
