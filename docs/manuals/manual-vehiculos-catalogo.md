# Guía de vehículos y catálogo

Creación, edición, publicación y control del estado comercial de vehículos.

- Tipo: `context`
- Categoría: `operacion-comercial`
- Permiso requerido: `vehicles.view`
- Roles específicos: `según permisos`
- Ruta contextual: `vehicles_internal:list`

Guía de vehículos y catálogo

Objetivo
Mantener fichas vehiculares confiables y publicar únicamente unidades disponibles.

Procedimiento recomendado
1. Busca primero por código interno, VIN real, marca o modelo para evitar duplicados.
2. Registra el VIN real solo cuando haya sido asignado por el fabricante.
3. Completa precio, sucursal, estado, descripción e imágenes.
4. Publica únicamente vehículos disponibles y autorizados para catálogo.
5. Actualiza el estado al reservar, vender, ocultar o archivar.

Controles importantes
• Nunca inventes un VIN legal.
• Una unidad reservada o vendida no debe mostrarse públicamente.

Antes de terminar
□ Código interno único.
□ Estado coherente.
□ Imágenes y datos comerciales revisados.
