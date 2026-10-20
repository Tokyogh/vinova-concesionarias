# Transfer de instalaciones VINOVA

Estado: **IMPLEMENTED / VERIFIED (N12 primitives/CLI)**.

Transfer mueve el estado portable de una instalación single-tenant a otra infraestructura. No actualiza VINOVA, no
contiene código fuente y no sustituye un backup de recuperación.

## Exportar

```bash
python manage.py export_vinova_installation /ruta/segura/installation.vinova
```

El contenedor incluye manifest, fixture lógica de base de datos, media y archivos privados portables. No copia un dump
físico opaco: la exportación desactiva clientes API/webhooks y elimina hashes de contraseña, secretos MFA, códigos de
respaldo, sesiones activas e historial de contraseñas para obligar su reprovisionamiento. El manifest registra:

- product version;
- transfer format version;
- ledger/fingerprint de migraciones;
- timestamp;
- inventario de componentes;
- tamaño y SHA-256 de cada archivo;
- metadata de secretos a reprovisionar.

Se excluyen `.env`, credenciales QA, claves/certificados, sesiones, reportes QA y backups anidados. Los secretos no se
copian: deben provisionarse por un canal seguro en el destino.

## Validar antes de importar

```bash
python manage.py validate_vinova_transfer installation.vinova --destination /ruta/de/staging
```

La validación falla ante extensión/formato incorrectos, path traversal, links o tipos TAR no permitidos, miembros
duplicados, inventario incompleto, hash/tamaño alterado, secretos declarados como incluidos, versión futura o espacio
insuficiente. Un paquete de una versión anterior requiere una ruta forward explícita:

```bash
python manage.py validate_vinova_transfer installation.vinova --allow-forward-migration
```

## Preparar importación

```bash
python manage.py prepare_vinova_import installation.vinova \
  --destination /ruta/aislada/vinova-import \
  --confirm PREPARE_IMPORT
```

El destino debe estar vacío. El comando valida de nuevo y extrae únicamente a ese staging; no ejecuta restore, no
aplica migraciones y no toca producción. Después se deben reprovisionar secretos, restaurar la base con herramientas
del motor correspondiente, desplegar media/private, ejecutar migraciones/checks y validar la aplicación antes del
cambio de tráfico.

No importe un paquete futuro en código antiguo. No use `--allow-forward-migration` sin evidencia de compatibilidad.
