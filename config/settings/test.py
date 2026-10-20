"""ES: Este módulo implementa el componente test para el dominio de configuración.

EN: This module implements the test component for the configuration domain.

Contexto existente / Existing context:
Vinova runtime configuration for test.
"""

from pathlib import Path
from tempfile import gettempdir

from .base import *  # noqa: F403

DEBUG = False
ALLOWED_HOSTS = ["testserver", "localhost", "127.0.0.1"]

QA_RUNTIME_ROOT = Path(  # noqa: F405
    env("VINOVA_QA_RUNTIME_ROOT", default=str(Path(gettempdir()) / "vinova-qa-runtime"))  # noqa: F405
).resolve()
QA_RUNTIME_ROOT.mkdir(parents=True, exist_ok=True)
STATIC_ROOT = QA_RUNTIME_ROOT / "staticfiles"
MEDIA_ROOT = QA_RUNTIME_ROOT / "media"
PRIVATE_STORAGE_ROOT = QA_RUNTIME_ROOT / "private"
VINOVA_QA_REPORT_ROOT = Path(  # noqa: F405
    env("VINOVA_QA_REPORT_ROOT", default=str(PRIVATE_STORAGE_ROOT / "qa_reports"))  # noqa: F405
).resolve()

TEST_DATABASE_URL = env("TEST_DATABASE_URL", default="")  # noqa: F405
if TEST_DATABASE_URL:
    DATABASES = {"default": env.db("TEST_DATABASE_URL")}  # noqa: F405
else:
    DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": QA_RUNTIME_ROOT / "test.sqlite3"}}
CACHES = {"default": {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"}}

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True
VINOVA_BACKUP_SYNC_FALLBACK = False
VINOVA_REQUIRE_CELERY_READY = False
VINOVA_API_DOCS_PUBLIC = False
