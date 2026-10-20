"""ES: Este módulo implementa el componente local para el dominio de configuración.

EN: This module implements the local component for the configuration domain.

Contexto existente / Existing context:
Vinova runtime configuration for local.
"""

from .base import *  # noqa: F403

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "0.0.0.0", "testserver"]
CSRF_TRUSTED_ORIGINS = ["http://localhost:8000", "http://127.0.0.1:8000"]
VINOVA_BACKUP_SYNC_FALLBACK = env.bool("VINOVA_BACKUP_SYNC_FALLBACK", default=True)  # noqa: F405
VINOVA_REQUIRE_CELERY_READY = env.bool("VINOVA_REQUIRE_CELERY_READY", default=False)  # noqa: F405
VINOVA_API_DOCS_PUBLIC = env.bool("VINOVA_API_DOCS_PUBLIC", default=True)  # noqa: F405
