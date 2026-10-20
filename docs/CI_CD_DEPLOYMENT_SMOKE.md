# Integración CI/CD del Deployment Smoke

## Staging

```bash
export VINOVA_SMOKE_BASE_URL="https://staging.vinova.com"
export VINOVA_SMOKE_USERNAME="$SMOKE_USERNAME"
export VINOVA_SMOKE_PASSWORD="$SMOKE_PASSWORD"
export VINOVA_SMOKE_ALLOW_WRITE="true"
./scripts/qa-deployment-smoke.sh --mode staging --write-tests --cleanup
```

Conserve como artefactos de la ejecución:

```text
private/qa_reports/deployment-smoke-*/summary.json
private/qa_reports/deployment-smoke-*/report.html
private/qa_reports/deployment-smoke-*/junit.xml
private/qa_reports/deployment-smoke-*/evidence.zip
```

## Producción

```bash
export VINOVA_SMOKE_BASE_URL="https://vinova.empresa.com"
export VINOVA_SMOKE_USERNAME="$PROD_SMOKE_USERNAME"
export VINOVA_SMOKE_PASSWORD="$PROD_SMOKE_PASSWORD"
./scripts/qa-deployment-smoke.sh --mode production
```

La cuenta de producción debe ser de solo lectura. El pipeline debe detener la publicación si el proceso devuelve `1`, `4` o `5`. El código `6` requiere intervención inmediata para revisar datos ficticios no neutralizados.

## Secretos

Use el almacén de secretos del proveedor CI. No escriba contraseñas en YAML, comandos visibles, archivos `.env` versionados o artefactos.
