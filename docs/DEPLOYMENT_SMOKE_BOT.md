# Vinova Deployment Smoke Bot

Estado del código fuente: **Vinova Pro 2.0.0**. Este bot es una capa separada de `qa-full`, `qa-release` y los E2E aislados de Docker.

## Alcance

El runner comprueba una instalación externa por URL real y genera siempre:

- `summary.json`
- `report.html`
- `junit.xml`
- `screenshots/`, `traces/` y `videos/` cuando correspondan
- `evidence.zip`

Directorio predeterminado:

```text
private/qa_reports/deployment-smoke-<timestamp>-<run_id>/
```

## Requisitos

```text
Python 3.12
playwright >= 1.60,<1.61
navegador Playwright instalado
```

Instalación local de dependencias QA:

```bash
python -m pip install -r requirements/local.txt
python -m playwright install chromium firefox webkit
```

## Variables

```text
VINOVA_SMOKE_BASE_URL
VINOVA_SMOKE_USERNAME
VINOVA_SMOKE_PASSWORD
VINOVA_SMOKE_TIMEOUT
VINOVA_SMOKE_RETRIES
VINOVA_SMOKE_REPORT_DIR
VINOVA_SMOKE_ALLOW_WRITE
VINOVA_SMOKE_DEMO_CONFIRM
VINOVA_SMOKE_RETAIN_CONFIRM
VINOVA_SMOKE_ROLE_CREDENTIALS_FILE
VINOVA_SMOKE_ALLOW_ROLE_PROVISION
```

Las contraseñas no se escriben en argumentos en CI; se cargan como secretos del entorno. El bot no registra cookies, tokens ni contraseñas.

## Producción no destructiva

```powershell
scripts\qa-deployment-smoke.cmd https://vinova.empresa.com --mode production
```

Comprueba DNS, TLS, redirección a HTTPS, portada, recursos, login, healthchecks, navegación privada, seguridad, matriz de roles, responsive y logout. No ejecuta flujos de negocio de escritura. El escenario `roles` requiere un manifest técnico previamente preparado; en producción nunca se crean cuentas automáticamente.

Escenario dirigido sin credenciales:

```powershell
scripts\qa-deployment-smoke.cmd https://vinova.empresa.com --scenario tls
scripts\qa-deployment-smoke.cmd https://vinova.empresa.com --scenario public
```


### Dependencia entre escenarios dirigidos

Cuando se ejecute `health` de forma aislada y se quiera validar `/health/dependencies/`, incluya primero `--scenario auth` en la misma ejecución. El control autenticado requiere una sesión activa y una cuenta `is_staff=True`.

El flujo de Inventario vuelve a seleccionar la sucursal después de cada redirección y valida el formulario antes de esperar navegación, evitando timeouts causados por validación HTML nativa.

## Matriz automática de roles en local

```powershell
scripts\qa-deployment-smoke-roles-local.cmd
```

Crea cuentas temporales, ejecuta la matriz completa y las desactiva en un bloque `finally`. El reporte HTML incluye el resultado permitido/bloqueado por rol y capacidad.

## Staging con escritura y limpieza

Se requieren dos autorizaciones independientes:

```powershell
$env:VINOVA_SMOKE_ALLOW_WRITE="true"
scripts\qa-deployment-smoke.cmd https://staging.vinova.com --mode staging --write-tests --cleanup
```

Los registros creados contienen `SMOKE-<run_id>`. La limpieza se ejecuta aun si otro control falla. Debido al modelo de trazabilidad de Vinova, “limpieza” significa archivar clientes, vehículos, artículos y documentos; anular comprobantes, cancelar ventas y marcar leads como perdidos. No se realiza borrado físico ni se elimina auditoría.

## Demostración empresarial

```powershell
$env:VINOVA_SMOKE_ALLOW_WRITE="true"
scripts\qa-deployment-smoke.cmd https://demo.vinova.com --mode demo --confirm-demo-target demo.vinova.com --record-video --cleanup
```

El hostname debe confirmarse literalmente. El modo demo no se ejecuta en producción.

Para conservar datos ficticios:

```powershell
scripts\qa-deployment-smoke.cmd https://demo.vinova.com --mode demo --confirm-demo-target demo.vinova.com --retain-demo-data --confirm-retain-demo-data RETAIN-demo.vinova.com
```

## Escenarios permitidos

```text
public tls assets health auth navigation security roles customers vehicles inventory sales documents accessibility cleanup demo all
```

No se aceptan nombres arbitrarios ni listas con comas. Para varios escenarios, repita `--scenario`.

## Códigos de salida

```text
0 controles obligatorios aprobados
1 uno o más controles fallaron
2 argumentos inválidos
3 configuración incompleta o insegura
4 credenciales ausentes
5 objetivo inaccesible por DNS
6 limpieza incompleta
```

## Consideraciones operativas

- TLS se valida con el almacén de confianza del sistema. No existe `verify=False` ni `ignore-certificate-errors`.
- Los reintentos se aplican únicamente a DNS, TLS, navegación y recursos potencialmente transitorios.
- `/health/dependencies/` se consulta solo con una cuenta staff; `/health/live/` y `/health/ready/` son públicos.
- La matriz de roles usa un manifest efímero con los 13 roles y un usuario inactivo. El manifest se elimina después de la ejecución local automática.
- La creación automática de cuentas está bloqueada en producción y requiere autorización explícita en local/staging/demo.
- La cuenta principal de staging/demo debe tener permisos mínimos para los módulos que se ejecuten.

## CI/CD

Secuencia recomendada:

```text
qa-release aprobado
→ despliegue staging
→ smoke de lectura
→ smoke staging con escritura y cleanup
→ aprobación manual
→ despliegue producción
→ smoke production no destructivo
```

No se debe declarar el despliegue aprobado si `deployment_ready=false`.
