# Instalación de Vinova Pro 2.0.0

## Requisitos

- Docker Desktop con WSL2 en Windows, o Docker Engine/Compose.
- Git opcional.
- Puertos libres: 8000, 5432, 6379, 8025 y 1025.

## Primera instalación

```bash
cp .env.example .env
# Editar SECRET_KEY y VINOVA_API_TOKEN_PEPPER antes de usar datos reales.
docker compose build
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py seed_roles
docker compose run --rm web python manage.py seed_api_scopes
docker compose run --rm web python manage.py seed_help_center
docker compose run --rm web python manage.py createsuperuser
docker compose up -d --remove-orphans
docker compose ps
```

Accesos:

```text
Aplicación: http://localhost:8000
Swagger v1: http://localhost:8000/api/v1/docs/
Swagger compatible: http://localhost:8000/api/docs/
Mailpit: http://localhost:8025
```

## Actualización de una instalación existente

Conserva `.env`, `media/`, `private/` y volúmenes:

```bash
docker compose down
docker compose build
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py seed_roles
docker compose run --rm web python manage.py seed_api_scopes
docker compose run --rm web python manage.py seed_help_center
docker compose up -d --remove-orphans
docker compose ps
```

No uses `docker compose down -v` en una actualización normal.

## Verificación

```bash
docker compose exec web python manage.py check
docker compose exec web python manage.py check_celery
docker compose exec celery_worker celery -A config inspect registered
```

El worker principal debe consumir `default,backups,webhooks`.

## Preparar la automatización QA

La instalación normal no activa el QA Bot. Para validaciones empresariales use el Compose adicional y los scripts de un solo comando:

```powershell
.\scripts\vinova-qa.ps1 quick
.\scripts\vinova-qa.ps1 full
.\scripts\vinova-qa.ps1 release
```

En Linux/WSL:

```bash
./scripts/vinova-qa.sh quick
```

Los perfiles levantan recursos QA aislados y no deben apuntar a la base de datos empresarial.
