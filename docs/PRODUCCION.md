# Operación en producción

## 1. Requisitos

- Docker Engine/Compose actual o Docker Desktop.
- Dominio y DNS.
- Certificados TLS o proxy/balanceador TLS controlado.
- 4 GB RAM mínimos recomendados para una instalación pequeña; ajustar Worker y PostgreSQL según carga.
- Copia externa para backups.
- Motor antivirus/CDR o cuarentena de archivos externos, si el release admite uploads de ese origen.

## 2. Preparación

El `Dockerfile` instala exclusivamente `requirements/production.lock` con
`--require-hashes`. No edite ese archivo a mano ni cambie el argumento de build a
un `.txt` sin regenerar, auditar y probar el lock. Las imágenes externas de Compose
están fijadas por digest; una renovación debe registrar el nuevo digest y repetir
los gates descritos en `docs/seguridad-avanzada/11-cadena-suministro.md`.

Para cada candidato regenere el SBOM, ejecute `pip-audit` sobre el lock y Trivy
sobre las imágenes construidas. La evidencia local no sustituye el digest del
artefacto publicado ni su firma/attestation en el registro autorizado.

```bash
cp .env.production.example .env
```

Edite todos los valores `CHANGE-*`. `COMPOSE_PROFILES=local-db` activa PostgreSQL en Compose. Para una base administrada, elimine esa variable y apunte `DATABASE_URL` al servicio externo. Genere `SECRET_KEY` una sola vez y consérvela. Cambiarla invalida sesiones, firmas y secretos 2FA cifrados. Genere también `VINOVA_API_TOKEN_PEPPER` como un secreto diferente de al menos 32 caracteres; cambiarlo invalida todos los tokens API.

Para TLS nativo coloque, fuera del control de versiones:

```text
docker/nginx/certs/fullchain.pem
docker/nginx/certs/privkey.pem
```

Configure:

```env
NGINX_TLS_ENABLED=True
NGINX_SERVER_NAME=vinova.example.com
ALLOWED_HOSTS=vinova.example.com
CSRF_TRUSTED_ORIGINS=https://vinova.example.com
VINOVA_HEALTHCHECK_HOST=vinova.example.com
VINOVA_TRUST_PROXY_HEADERS=True
```

Si un balanceador **controlado** termina TLS antes de Nginx, use `NGINX_TLS_ENABLED=False` y `NGINX_FORWARDED_PROTO=https`. Es un valor fijo de infraestructura; Nginx no reutiliza el header enviado libremente por el cliente. No configure `https` cuando el acceso directo al servidor sea HTTP.
Para conservar la IP real, configure además `NGINX_TRUSTED_PROXY_CIDR` con la IP o red exacta del balanceador, por ejemplo `10.20.0.0/24`. Si queda vacío, Nginx ignora la cadena de IP enviada por el cliente y usa la dirección que observa directamente.

## 3. Primera puesta en marcha

```bash
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d --remove-orphans
docker compose -f docker-compose.prod.yml ps
docker compose -f docker-compose.prod.yml logs app_init
```

`app_init` debe terminar correctamente. Luego:

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py seed_roles
docker compose -f docker-compose.prod.yml exec web python manage.py seed_api_scopes
docker compose -f docker-compose.prod.yml exec web python manage.py seed_help_center
docker compose -f docker-compose.prod.yml exec web python manage.py createsuperuser
docker compose -f docker-compose.prod.yml exec web python manage.py check_celery
```

No ejecute seeds de demostración en producción sin revisar su idempotencia y necesidad.

## 4. Actualización entre versiones

1. Cree y verifique un backup.
2. Conserve `.env`, `media`, `private` y volúmenes.
3. Registre la imagen/versión actual para rollback.
4. Detenga servicios sin borrar volúmenes.
5. Reemplace el código.
6. Construya y levante.

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py create_vinova_backup --type full
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d --remove-orphans
docker compose -f docker-compose.prod.yml exec web python manage.py seed_roles
docker compose -f docker-compose.prod.yml exec web python manage.py seed_api_scopes
docker compose -f docker-compose.prod.yml exec web python manage.py seed_help_center
```

## 5. Rollback lógico

Un rollback de código no siempre puede deshacer migraciones. Procedimiento:

1. no borrar volúmenes;
2. detener la versión nueva;
3. restaurar la imagen/código anterior;
4. revisar compatibilidad de esquema;
5. si es necesario, restaurar una copia verificada en un entorno aislado y documentar la decisión.

Nunca aplique `migrate app zero` o `docker compose down -v` como rollback improvisado.

## 6. Celery

```bash
docker compose -f docker-compose.prod.yml logs --tail=200 redis
docker compose -f docker-compose.prod.yml logs --tail=200 celery_worker
docker compose -f docker-compose.prod.yml logs --tail=200 celery_beat
docker compose -f docker-compose.prod.yml exec celery_worker celery -A config inspect ping
docker compose -f docker-compose.prod.yml exec celery_worker celery -A config inspect registered
docker compose -f docker-compose.prod.yml exec web python manage.py check_celery
```

Solo debe existir una instancia de Beat. Puede escalar Workers, pero asegure que todos consuman `default,backups,webhooks` o separe workers por cola de forma deliberada.

Celery puede mostrar anotaciones como `apps.continuity.tasks.run_backup_task [rate_limit=2/h]`; la anotación no significa que la tarea esté ausente. `task events: OFF` solo indica que el stream opcional de eventos está desactivado.

## 7. Backups

Producción no usa fallback síncrono. Si Redis o Worker están caídos, el backup web falla de forma visible y auditada.

```bash
docker compose -f docker-compose.prod.yml exec web python manage.py create_vinova_backup --type full
docker compose -f docker-compose.prod.yml exec web python manage.py verify_vinova_backup UUID
```

El comando administrativo es síncrono a propósito y es útil durante incidentes, siempre que PostgreSQL y el storage estén disponibles.

Para activar programación:

```env
VINOVA_AUTOMATED_BACKUPS_ENABLED=True
```

Revise primero frecuencia, capacidad de disco, retención y copia externa. La activación puede crear el primer backup cuando Beat detecte una política vencida o sin éxitos previos.

## 8. SMTP

Use TLS o SSL según el proveedor, nunca ambos:

```env
EMAIL_HOST=smtp.example.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_USE_SSL=False
EMAIL_HOST_USER=...
EMAIL_HOST_PASSWORD=...
```

Supervise errores del logger `django` y pruebe restablecimiento de contraseña antes de abrir el sistema.

## 9. Almacenamiento

La configuración local usa volúmenes para `media` y `private`. Los avatares pueden
usar Cloudinary con `STORAGE_BACKEND=cloudinary` y las tres variables
`CLOUDINARY_*`. Los documentos sensibles pueden usar un servicio S3-compatible
(S3, R2 o MinIO) con `PRIVATE_STORAGE_BACKEND=s3`, endpoint, credenciales y bucket.
El backend privado no publica dominio, usa URLs firmadas cortas, ACL privada y
cifrado de objetos `AES256`.

Antes de activar un proveedor, copie todos los archivos existentes y valide sus
hashes. No cambie el backend con archivos pendientes de migración: los registros
conservan la clave del objeto, no el proveedor histórico. El fallback local evita
que una configuración incompleta impida arrancar, pero `/health/ready/` y
`check_release_readiness --strict` la reportan como inválida.

En staging, después de cargar credenciales reales, ejecute el ciclo temporal:

```bash
python manage.py check_storage_integrations --live
```

El comando crea, lee, genera URL y elimina objetos temporales sin imprimir
credenciales. Verifique además reemplazo y borrado de avatar, descarga protegida,
caducidad de URL, política de bucket sin acceso público y recuperación ante caída
del proveedor. Sin `--live`, el comando solo realiza probes no destructivos.

## 10. Monitoreo

Supervise:

- estado Docker y reinicios;
- `/health/ready/`;
- espacio de PostgreSQL, media, private y backups;
- duración/fallos de backups;
- cola Redis;
- errores 5xx y latencia;
- expiración TLS;
- SMTP;
- eventos de auditoría e integridad.

Sentry es opcional. Mantenga `send_default_pii=False` y no adjunte payloads sensibles.

Supervise también entregas webhook fallidas, crecimiento de `IntegrationLog`, tokens próximos a vencer y errores 401/403 anómalos. No registre cabeceras `Authorization` ni secretos de firma.

## 11. Logs

```bash
docker compose -f docker-compose.prod.yml logs -f web
docker compose -f docker-compose.prod.yml logs -f celery_worker
docker compose -f docker-compose.prod.yml logs -f celery_beat
docker compose -f docker-compose.prod.yml logs -f nginx
```

Compose rota logs con `max-size=10m` y `max-file=5`. En instalaciones reguladas use un colector central con retención definida y acceso restringido.

## 12. Comprobación de preparación

Antes y después de una actualización, ejecute:

```bash
python manage.py check_release_readiness --database --strict
```

Con Redis y Workers activos:

```bash
python manage.py check_release_readiness --database --with-celery --strict
```

La comprobación valida configuración y conectividad, pero no sustituye la prueba
visual, el ensayo de restauración ni el monitoreo posterior al despliegue.
Mantenga la política Staff en `off` hasta probar redes/VPN, dos aprobadores con
2FA, expiración/revocación y recuperación. Verifique también rechazo/aceptación
granular de cookies, bloqueo previo de MapTiler/analítica, cuarentena/antivirus y
restricciones de dominio de claves públicas.

## QA empresarial

Las validaciones automáticas se ejecutan en el perfil Docker QA, separado de los servicios de producción. No habilite `VINOVA_QA_EXECUTION_ENABLED` en el contenedor web de producción ni monte el socket de Docker dentro de Vinova Pro. El runner acepta únicamente los perfiles cerrados `quick`, `full` y `release`, usa una base PostgreSQL temporal y conserva los reportes en almacenamiento privado.

```bash
docker compose -f docker-compose.prod.yml -f docker-compose.qa.yml --profile qa up -d web celery_worker celery_beat qa_worker
docker compose --project-name vinova-qa-cli -f docker-compose.qa-cli.yml run --rm qa_runner \
  python scripts/vinova_qa.py --profile release
```

El worker `qa_worker` consume exclusivamente la cola `qa`, usa concurrencia uno y debe permanecer aislado del tráfico HTTP público.
