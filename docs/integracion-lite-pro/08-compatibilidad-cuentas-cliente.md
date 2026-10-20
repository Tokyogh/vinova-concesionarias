# Compatibilidad de cuentas cliente anteriores a LITE → PRO

Fecha: 2026-10-11
Rama: `integration/lite-pro`

## Causa exacta

El acceso al portal exige dos condiciones independientes:

1. La cuenta activa debe conservar una asignación vigente cuyo rol otorgue `portal.access`.
2. Debe existir un único `Customer` elegible vinculado mediante `Customer.account`.

Las cuentas locales afectadas cumplían la primera condición, pero fueron creadas antes de que la integración incorporara `Customer.account` y no tenían ningún expediente vinculado. `portal_customer_for_user()` filtraba por esa relación y elevaba `Http404`; por eso `/mi-cuenta/` mostraba el mensaje técnico. La migración `customers.0003_customer_account` sí estaba aplicada: el problema era de datos heredados, no de esquema.

La auditoría local encontró dos cuentas activas afectadas, `Prueba0` (id 2) y `qa.cliente` (id 114). Ninguna tenía un `Customer` asociado ni un candidato por correo. No se usaron correo, identificación o nombre para decidir un vínculo.

## Corrección

- El resolver solo considera elegibles expedientes no eliminados con estado `active` o `vip`.
- Una cuenta autenticada con `portal.access`, pero sin expediente elegible, recibe una página segura con HTTP 409 que solicita vinculación o activación. Las cuentas sin permiso siguen recibiendo HTTP 403.
- El procedimiento QA crea un expediente nuevo solo para un `User.id` indicado explícitamente y lo vincula mediante `link_customer_account()`.
- La creación usa `create_customer_from_data()`; ambos pasos generan auditoría.
- El procedimiento no cambia contraseñas, roles, permisos ni expedientes existentes.
- Se rechazan cuentas inactivas, Staff/superusuario, cuentas sin rol cliente y `portal.access` vigentes, operadores sin `customers.manage`, falta de alcance de sucursal, expedientes inactivos ya vinculados y cualquier candidato por correo. Un candidato se considera ambiguo y nunca se vincula automáticamente.
- Reejecutar el procedimiento para una cuenta ya vinculada y elegible no crea filas ni eventos de auditoría adicionales.

## Preparación segura de una cuenta QA heredada

Este comando está bloqueado en producción y exige el ID exacto de la cuenta y de un operador autorizado:

```powershell
python manage.py prepare_qa_client_account --user-id <ID_CUENTA> --actor-id <ID_OPERADOR>
python manage.py prepare_qa_client_account --user-id <ID_CUENTA> --actor-id <ID_OPERADOR> --apply
```

La primera ejecución es una previsualización sin cambios. Antes de usar `--apply`, el operador debe confirmar por un canal confiable que el ID pertenece a una cuenta de prueba. Si existe cualquier expediente candidato, se debe resolver manualmente desde el flujo empresarial; no se debe forzar el comando ni asociar por coincidencia de datos personales.

Para activar un expediente existente se conserva el flujo empresarial normal. Este comando no reactiva expedientes archivados, inactivos o eliminados.

## Resultado local

- Cuenta 2: expediente 7 creado y vinculado mediante servicios auditados.
- Cuenta 114: expediente 8 creado y vinculado mediante servicios auditados.
- Segunda ejecución: sin cambios para ambas cuentas.
- Resolución posterior: ambas cuentas recuperan su expediente activo. `qa.cliente` abre el dashboard con HTTP 200. `Prueba0` conserva su gate previo `must_change_password` y es redirigida al cambio obligatorio antes del portal; no se alteraron esa bandera ni su contraseña.
- No se modificaron contraseñas ni se crearon migraciones.

## Cobertura de regresión

Las pruebas cubren cliente con vínculo válido, expediente VIP, ausencia de expediente, estados inactivo/archivado, borrado lógico, permiso vencido o ausente, cuenta Staff, dos clientes distintos, propiedad horizontal de vehículos y documentos, expediente previamente vinculado, candidato ambiguo, preservación de contraseña, auditoría, bloqueo en producción e idempotencia.
