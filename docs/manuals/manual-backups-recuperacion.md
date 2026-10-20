# Manual de backups y recuperación

Creación, verificación, descarga protegida y preparación de restauraciones.

- Tipo: `manual`
- Categoría: `continuidad`
- Permiso requerido: `continuity.view`
- Roles específicos: `según permisos`
- Ruta contextual: `continuity:dashboard`

Manual de backups y recuperación

Objetivo
Mantener copias verificables y preparar recuperaciones sin restaurar producción desde una pantalla web.

Procedimiento recomendado
1. Revisa que Redis, Worker y Beat estén saludables.
2. Crea el tipo de backup necesario: base, archivos o completo.
3. Confirma que pase por en cola, ejecutando y completado.
4. Verifica tamaño, manifiesto y SHA-256.
5. Conserva una copia externa protegida.
6. Ejecuta simulacros de restauración en un entorno aislado.
7. Documenta resultado y acciones correctivas.

Controles importantes
• No incluyas private/backups dentro de sí mismo.
• No restaures producción automáticamente desde la web.
• No uses down -v en una actualización normal.

Antes de terminar
□ Último backup completado.
□ Hash verificado.
□ Copia externa vigente.
□ Simulacro programado.
