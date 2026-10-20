# Mapa funcional — Instituciones públicas

Evidencia: [09-instituciones-mapa.png](capturas/09-instituciones-mapa.png)

Ruta: `/instituciones/`

## Flujo de datos

`PublicInstitutionListView` obtiene `public_institution_queryset()`. El selector solo publica `Branch` activas, marcadas `is_public`, pertenecientes a una compañía activa y con tipo `institution`, `office`, `dealership` o `service_center`. El orden estable es tipo, nombre y clave primaria.

| Componente señalado | Fuente | Transformación e interacción | Vacío y seguridad |
|---|---|---|---|
| Tipos y conteos | `Branch.branch_type` y `Branch.public_category` | Oficina e institución se agrupan como institución; concesionaria y centro de atención conservan categorías separadas. Los controles filtran la colección ya publicada. | Una categoría sin sedes queda en cero; no revela sedes privadas o inactivas. |
| Lista de sedes | `name`, `city`, `province`, `address`, `phone`, `opening_hours`, `description`, `services`, `photo`, `website_url` | `public_services` limpia, limita a seis entradas y trunca cada etiqueta; `phone_uri` elimina caracteres no marcables para el enlace telefónico. | Campos opcionales omiten su bloque o muestran el texto neutral definido por el template. No se inventan direcciones ni contactos. |
| Mapa | `latitude`, `longitude`, `name`, `public_category` | JavaScript crea marcadores únicamente cuando ambas coordenadas existen (`has_map_coordinates`). MapTiler se carga solo cuando existe clave pública y la categoría de medios externos fue aceptada. | Sin consentimiento, clave, coordenadas o proveedor se conserva la lista y se muestra el fallback controlado; la clave no se imprime en la documentación. |
| Panel de detalle | Proyección pública de la sede seleccionada | La selección desde lista o marcador sincroniza el panel, sin efectuar una mutación de servidor. | Ninguna acción pública permite editar una sede. |

## Quién puede modificar la información

Las sedes se administran desde las interfaces internas y servicios del dominio `branches`, sujetos a sus permisos y alcance. La página pública solo lee la proyección autorizada. Las coordenadas tienen validadores de latitud `[-90, 90]` y longitud `[-180, 180]`; `website_url` solo acepta HTTP/HTTPS y los uploads de foto pasan validación de extensión y tamaño.

La captura usa una sede sintética en Quito (`-0.180653`, `-78.467834`) creada dentro de la base E2E. La prueba verifica los cuatro componentes, respuesta 200 y ausencia de overflow. Las pruebas del dominio cubren publicación, coordenadas, filtros y fallback.
