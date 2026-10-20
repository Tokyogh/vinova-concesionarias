# Matriz automática de roles

La matriz crea cuentas temporales para los 13 roles de sistema y un usuario inactivo. Evalúa el dashboard asignado y rutas de lectura/gestión mediante acceso directo, no solo por visibilidad de botones.

## Local automático

```powershell
scripts\qa-deployment-smoke-roles-local.cmd
```

El script:

1. crea cuentas `smoke.role.<run_id>.<rol>`;
2. ejecuta el escenario `roles`;
3. genera JSON, HTML, JUnit, capturas y evidencia ZIP;
4. desactiva todas las cuentas y sucursales temporales aunque falle una prueba;
5. elimina el manifest local con contraseñas.

La creación automática exige `VINOVA_SMOKE_ALLOW_ROLE_PROVISION=true` y solo está permitida en local, staging, demo o test. En producción deben proporcionarse cuentas técnicas previamente creadas.
