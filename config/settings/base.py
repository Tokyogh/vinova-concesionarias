"""ES: Este módulo implementa el componente base para el dominio de configuración.

EN: This module implements the base component for the configuration domain.

Contexto existente / Existing context:
Vinova runtime configuration for base.
"""

from __future__ import annotations

from pathlib import Path

import environ
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent.parent
VINOVA_PRODUCT_VERSION = "2.0.0"
VINOVA_BACKUP_FORMAT_VERSION = 3
VINOVA_TRANSFER_FORMAT_VERSION = 1

env = environ.Env(
    DEBUG=(bool, False),
    SECRET_KEY=(str, "unsafe-local-dev-key-change-me"),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1"]),
    CSRF_TRUSTED_ORIGINS=(list, []),
    DATABASE_URL=(str, "postgres://vinova:vinova@db:5432/vinova_pro"),
    REDIS_URL=(str, "redis://redis:6379/0"),
    EMAIL_PORT=(int, 1025),
    MAPTILER_PUBLIC_KEY=(str, ""),
)
if not env.bool("VINOVA_QA_IGNORE_PROJECT_ENV", default=False) and (BASE_DIR / ".env").exists():
    environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")
CSRF_TRUSTED_ORIGINS = env("CSRF_TRUSTED_ORIGINS")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "django_filters",
    "drf_spectacular",
    "apps.common.apps.CommonConfig",
    "apps.accounts.apps.AccountsConfig",
    "apps.companies.apps.CompaniesConfig",
    "apps.branches.apps.BranchesConfig",
    "apps.vehicles.apps.VehiclesConfig",
    "apps.inventory.apps.InventoryConfig",
    "apps.customers.apps.CustomersConfig",
    "apps.sales.apps.SalesConfig",
    "apps.invoices.apps.InvoicesConfig",
    "apps.documents.apps.DocumentsConfig",
    "apps.notifications.apps.NotificationsConfig",
    "apps.reports.apps.ReportsConfig",
    "apps.enterprise.apps.EnterpriseConfig",
    "apps.sri_integration.apps.SriIntegrationConfig",
    "apps.imports.apps.ImportsConfig",
    "apps.leads.apps.LeadsConfig",
    "apps.analytics.apps.AnalyticsConfig",
    "apps.audit.apps.AuditConfig",
    "apps.continuity.apps.ContinuityConfig",
    "apps.privacy.apps.PrivacyConfig",
    "apps.security_center.apps.SecurityCenterConfig",
    "apps.dashboard.apps.DashboardConfig",
    "apps.api.apps.ApiConfig",
    "apps.help_center.apps.HelpCenterConfig",
    "apps.quality.apps.QualityConfig",
    "apps.post_sales.apps.PostSalesConfig",
    "apps.portal.apps.PortalConfig",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "apps.security_center.middleware.SecurityHeadersMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "apps.audit.middleware.AuditRequestMiddleware",
    "apps.api.middleware.APIIntegrationLogMiddleware",
    "apps.security_center.middleware.SecurityEnforcementMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.enterprise.context_processors.enterprise_public_context",
                "apps.help_center.context_processors.help_center_context",
                "apps.common.context_processors.optional_modules_context",
                "apps.common.context_processors.staff_shell_context",
                "apps.common.navigation.navigation_context",
                "apps.privacy.context_processors.cookie_preferences_context",
            ]
        },
    }
]
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["CONN_MAX_AGE"] = env.int("DB_CONN_MAX_AGE", default=60)
DATABASES["default"]["CONN_HEALTH_CHECKS"] = True
AUTH_USER_MODEL = "accounts.User"
AUTHENTICATION_BACKENDS = ["apps.accounts.backends.EmailOrUsernameBackend"]
VINOVA_MODULE_POST_SALES_ENABLED = env.bool("VINOVA_MODULE_POST_SALES_ENABLED", default=False)
VINOVA_PUBLIC_PARTS_CATALOG_ENABLED = env.bool("VINOVA_PUBLIC_PARTS_CATALOG_ENABLED", default=True)
VINOVA_VEHICLE_PLATE_PATTERN = env("VINOVA_VEHICLE_PLATE_PATTERN", default=r"^[A-Z]{2,3}[- ]?\d{3,4}$")
VINOVA_LOGIN_MAX_ATTEMPTS = env.int("VINOVA_LOGIN_MAX_ATTEMPTS", default=5)
VINOVA_LOGIN_LOCK_MINUTES = env.int("VINOVA_LOGIN_LOCK_MINUTES", default=15)
VINOVA_PUBLIC_FORM_MAX_SUBMISSIONS = env.int("VINOVA_PUBLIC_FORM_MAX_SUBMISSIONS", default=8)
VINOVA_PUBLIC_FORM_WINDOW_SECONDS = env.int("VINOVA_PUBLIC_FORM_WINDOW_SECONDS", default=3600)
VINOVA_COOKIE_NOTICE_VERSION = env("VINOVA_COOKIE_NOTICE_VERSION", default="2026-10-16")
VINOVA_COOKIE_CONSENT_NAME = env("VINOVA_COOKIE_CONSENT_NAME", default="vinova_cookie_preferences")
VINOVA_COOKIE_CONSENT_AGE = env.int("VINOVA_COOKIE_CONSENT_AGE", default=15552000)
VINOVA_PRIVACY_NOTICE_VERSION = env("VINOVA_PRIVACY_NOTICE_VERSION", default="draft-2026-10-16")
VINOVA_TERMS_VERSION = env("VINOVA_TERMS_VERSION", default="draft-2026-10-16")
LOGIN_URL = "accounts:login"
LOGIN_REDIRECT_URL = "accounts:profile"
LOGOUT_REDIRECT_URL = "accounts:login"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "apps.security_center.passwords.VinovaPasswordPolicyValidator"},
]

LANGUAGE_CODE = "es-ec"
TIME_ZONE = "America/Guayaquil"
USE_I18N = True
USE_TZ = True
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"
PRIVATE_STORAGE_ROOT = Path(env("PRIVATE_STORAGE_ROOT", default=str(BASE_DIR / "private")))
STORAGE_BACKEND = env("STORAGE_BACKEND", default="local").lower()
PRIVATE_STORAGE_BACKEND = env("PRIVATE_STORAGE_BACKEND", default="local").lower()
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Avatar uploads. CLOUDINARY_* se leen del entorno y nunca se versionan.
# Con STORAGE_BACKEND=cloudinary pero sin credenciales se usa almacenamiento local.
CLOUDINARY_CLOUD_NAME = env("CLOUDINARY_CLOUD_NAME", default="")
CLOUDINARY_API_KEY = env("CLOUDINARY_API_KEY", default="")
CLOUDINARY_API_SECRET = env("CLOUDINARY_API_SECRET", default="")
CLOUDINARY_HTTP_TIMEOUT_SECONDS = env.int("CLOUDINARY_HTTP_TIMEOUT_SECONDS", default=15)
MAPTILER_PUBLIC_KEY = env("MAPTILER_PUBLIC_KEY")

# Documentos privados. El backend S3-compatible solo se activa con todos los
# datos requeridos; el adaptador conserva fallback local para recuperación.
S3_ENDPOINT_URL = env("S3_ENDPOINT_URL", default="")
S3_ACCESS_KEY_ID = env("S3_ACCESS_KEY_ID", default="")
S3_SECRET_ACCESS_KEY = env("S3_SECRET_ACCESS_KEY", default="")
S3_BUCKET_NAME = env("S3_BUCKET_NAME", default="")
S3_REGION_NAME = env("S3_REGION_NAME", default="auto")
S3_ADDRESSING_STYLE = env("S3_ADDRESSING_STYLE", default="path").lower()
S3_PRIVATE_PREFIX = env("S3_PRIVATE_PREFIX", default="vinova/private").strip("/")
S3_SIGNED_URL_EXPIRE_SECONDS = env.int("S3_SIGNED_URL_EXPIRE_SECONDS", default=300)
S3_CONNECT_TIMEOUT_SECONDS = env.int("S3_CONNECT_TIMEOUT_SECONDS", default=5)
S3_READ_TIMEOUT_SECONDS = env.int("S3_READ_TIMEOUT_SECONDS", default=30)
VINOVA_AVATAR_MAX_MB = env.int("VINOVA_AVATAR_MAX_MB", default=5)
VINOVA_AVATAR_MIN_DIMENSION = env.int("VINOVA_AVATAR_MIN_DIMENSION", default=64)
VINOVA_AVATAR_MAX_DIMENSION = env.int("VINOVA_AVATAR_MAX_DIMENSION", default=4096)

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="mailpit")
EMAIL_PORT = env("EMAIL_PORT")
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=False)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)
EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=20)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", default="Vinova Pro <no-reply@localhost>")
SERVER_EMAIL = env("SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)

REDIS_URL = env("REDIS_URL")
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": REDIS_URL,
        "OPTIONS": {
            "socket_connect_timeout": env.int("REDIS_CONNECT_TIMEOUT", default=5),
            "socket_timeout": env.int("REDIS_SOCKET_TIMEOUT", default=5),
            "retry_on_timeout": True,
        },
    }
}
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=REDIS_URL)
CELERY_RESULT_BACKEND = env("CELERY_RESULT_BACKEND", default=REDIS_URL)
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True
CELERY_BROKER_CONNECTION_RETRY_ON_STARTUP = True
CELERY_BROKER_CONNECTION_MAX_RETRIES = env.int("CELERY_BROKER_CONNECTION_MAX_RETRIES", default=20)
CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_ACKS_LATE = True
CELERY_TASK_REJECT_ON_WORKER_LOST = True
CELERY_WORKER_PREFETCH_MULTIPLIER = env.int("CELERY_WORKER_PREFETCH_MULTIPLIER", default=1)
CELERY_RESULT_EXPIRES = env.int("CELERY_RESULT_EXPIRES", default=86400)
CELERY_TASK_DEFAULT_QUEUE = env("CELERY_TASK_DEFAULT_QUEUE", default="default")
CELERY_BACKUP_QUEUE = env("CELERY_BACKUP_QUEUE", default="backups")
CELERY_WEBHOOK_QUEUE = env("CELERY_WEBHOOK_QUEUE", default="webhooks")
CELERY_QA_QUEUE = env("CELERY_QA_QUEUE", default="qa")
CELERY_TASK_ROUTES = {
    "apps.continuity.tasks.run_backup_task": {"queue": CELERY_BACKUP_QUEUE},
    "apps.api.tasks.deliver_webhook_task": {"queue": CELERY_WEBHOOK_QUEUE},
    "apps.quality.tasks.run_quality_profile_task": {"queue": CELERY_QA_QUEUE},
}
CELERY_BROKER_TRANSPORT_OPTIONS = {
    "visibility_timeout": env.int("CELERY_VISIBILITY_TIMEOUT", default=14400),
    "health_check_interval": 30,
}
VINOVA_BACKUP_SOFT_TIME_LIMIT = env.int("VINOVA_BACKUP_SOFT_TIME_LIMIT", default=3300)
VINOVA_BACKUP_HARD_TIME_LIMIT = env.int("VINOVA_BACKUP_HARD_TIME_LIMIT", default=3600)
VINOVA_QA_SOFT_TIME_LIMIT = env.int("VINOVA_QA_SOFT_TIME_LIMIT", default=6900)
VINOVA_QA_HARD_TIME_LIMIT = env.int("VINOVA_QA_HARD_TIME_LIMIT", default=7200)
CELERY_TASK_ANNOTATIONS = {
    "apps.continuity.tasks.run_backup_task": {
        "soft_time_limit": VINOVA_BACKUP_SOFT_TIME_LIMIT,
        "time_limit": VINOVA_BACKUP_HARD_TIME_LIMIT,
        "rate_limit": env("VINOVA_BACKUP_TASK_RATE_LIMIT", default="2/h"),
    },
    "apps.quality.tasks.run_quality_profile_task": {
        "soft_time_limit": VINOVA_QA_SOFT_TIME_LIMIT,
        "time_limit": VINOVA_QA_HARD_TIME_LIMIT,
        "rate_limit": env("VINOVA_QA_TASK_RATE_LIMIT", default="4/h"),
    },
}
CELERY_BEAT_SCHEDULE = {
    "vinova-sales-expiry-scheduler": {
        "task": "apps.sales.tasks.expire_overdue_sales",
        "schedule": env.int("VINOVA_SALES_EXPIRY_INTERVAL", default=300),
    },
    "vinova-system-heartbeat": {
        "task": "apps.common.tasks.system_heartbeat",
        "schedule": env.int("VINOVA_CELERY_HEARTBEAT_INTERVAL", default=60),
    },
    "vinova-backup-policy-scheduler": {
        "task": "apps.continuity.tasks.schedule_policy_backups",
        "schedule": env.int("VINOVA_BACKUP_SCHEDULER_INTERVAL", default=300),
    },
    "vinova-daily-operational-checkpoint": {
        "task": "apps.common.tasks.system_heartbeat",
        "schedule": crontab(hour=3, minute=0),
    },
    "vinova-qa-daily-quick-check": {
        "task": "apps.quality.tasks.schedule_automated_quality_run",
        "schedule": crontab(hour=2, minute=30),
    },
    "vinova-qa-evidence-retention": {
        "task": "apps.quality.tasks.cleanup_quality_evidence_task",
        "schedule": crontab(hour=2, minute=50),
    },
}
VINOVA_CELERY_HEALTH_KEY = env("VINOVA_CELERY_HEALTH_KEY", default="vinova:health:celery_pipeline")
VINOVA_CELERY_HEARTBEAT_MAX_AGE = env.int("VINOVA_CELERY_HEARTBEAT_MAX_AGE", default=180)
VINOVA_REQUIRE_CELERY_READY = env.bool("VINOVA_REQUIRE_CELERY_READY", default=False)
VINOVA_BACKUP_SYNC_FALLBACK = env.bool("VINOVA_BACKUP_SYNC_FALLBACK", default=False)
VINOVA_AUTOMATED_BACKUPS_ENABLED = env.bool("VINOVA_AUTOMATED_BACKUPS_ENABLED", default=False)
VINOVA_BACKUP_PUBLISH_RETRY = env.bool("VINOVA_BACKUP_PUBLISH_RETRY", default=True)
VINOVA_BACKUP_PUBLISH_MAX_RETRIES = env.int("VINOVA_BACKUP_PUBLISH_MAX_RETRIES", default=3)
VINOVA_UPDATE_AGENT_STATUS_FILE = env("VINOVA_UPDATE_AGENT_STATUS_FILE", default="")
VINOVA_RELEASE_MANIFEST_PATH = env("VINOVA_RELEASE_MANIFEST_PATH", default="")
VINOVA_RELEASE_ARTIFACT_PATH = env("VINOVA_RELEASE_ARTIFACT_PATH", default="")
VINOVA_RELEASE_PUBLIC_KEY_PATH = env("VINOVA_RELEASE_PUBLIC_KEY_PATH", default="")
VINOVA_RELEASE_TRUSTED_KEY_ID = env("VINOVA_RELEASE_TRUSTED_KEY_ID", default="")

VINOVA_QA_EXECUTION_ENABLED = env.bool("VINOVA_QA_EXECUTION_ENABLED", default=False)
VINOVA_QA_AUTOMATED_ENABLED = env.bool("VINOVA_QA_AUTOMATED_ENABLED", default=False)
VINOVA_QA_AUTOMATED_MIN_INTERVAL_HOURS = env.int("VINOVA_QA_AUTOMATED_MIN_INTERVAL_HOURS", default=20)
VINOVA_QA_MAX_CONCURRENT_RUNS = env.int("VINOVA_QA_MAX_CONCURRENT_RUNS", default=1)
VINOVA_QA_STALE_AFTER_MINUTES = env.int("VINOVA_QA_STALE_AFTER_MINUTES", default=150)
VINOVA_QA_RETENTION_DAYS = env.int("VINOVA_QA_RETENTION_DAYS", default=90)
VINOVA_QA_ENVIRONMENT = env("VINOVA_QA_ENVIRONMENT", default="application")
VINOVA_QA_REPORT_ROOT = Path(env("VINOVA_QA_REPORT_ROOT", default=str(PRIVATE_STORAGE_ROOT / "qa_reports")))

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "apps.api.authentication.APIClientAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_FILTER_BACKENDS": [
        "apps.api.filtering.APIClientBranchScopeFilterBackend",
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 25,
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
        "apps.api.throttling.APIClientRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {"anon": "60/hour", "user": "1200/hour", "api_client": "600/hour"},
}
SPECTACULAR_SETTINGS = {
    "TITLE": "Vinova Pro API",
    "VERSION": VINOVA_PRODUCT_VERSION,
    "ENUM_NAME_OVERRIDES": {
        "LeadStatusEnum": "apps.leads.models.Lead.Status",
        "SaleStatusEnum": "apps.sales.models.SaleRecord.Status",
        "InvoiceStatusEnum": "apps.invoices.models.InvoiceRecord.Status",
        "LeadRequestTypeEnum": "apps.leads.models.Lead.RequestType",
        "PrivacyRequestTypeEnum": "apps.privacy.models.DataSubjectRequest.RequestType",
        "LeadPriorityEnum": "apps.leads.models.Lead.Priority",
        "NotificationPriorityEnum": "apps.notifications.models.NotificationMessage.Priority",
        "LeadSourceEnum": "apps.leads.models.Lead.Source",
        "SaleSourceEnum": "apps.sales.models.SaleRecord.Source",
        "QualityRunStatusEnum": "apps.quality.models.QualityRun.Status",
        "QualityCheckStatusEnum": "apps.quality.models.QualityCheckResult.Status",
    },
}
VINOVA_API_DOCS_PUBLIC = env.bool("VINOVA_API_DOCS_PUBLIC", default=True)

VINOVA_API_TOKEN_PEPPER = env("VINOVA_API_TOKEN_PEPPER", default=SECRET_KEY)
VINOVA_API_CLIENT_DEFAULT_RATE = env("VINOVA_API_CLIENT_DEFAULT_RATE", default="600/hour")
VINOVA_IDEMPOTENCY_TTL_HOURS = env.int("VINOVA_IDEMPOTENCY_TTL_HOURS", default=24)
VINOVA_WEBHOOK_ALLOW_PRIVATE_NETWORKS = env.bool("VINOVA_WEBHOOK_ALLOW_PRIVATE_NETWORKS", default=False)

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"
VINOVA_MAX_UPLOAD_MB = env.int("VINOVA_MAX_UPLOAD_MB", default=25)
VINOVA_ZIP_MAX_ENTRIES = env.int("VINOVA_ZIP_MAX_ENTRIES", default=1000)
VINOVA_ZIP_MAX_UNCOMPRESSED_MB = env.int("VINOVA_ZIP_MAX_UNCOMPRESSED_MB", default=100)
VINOVA_ZIP_MAX_COMPRESSION_RATIO = env.int("VINOVA_ZIP_MAX_COMPRESSION_RATIO", default=200)
VINOVA_IMPORT_MAX_ROWS = env.int("VINOVA_IMPORT_MAX_ROWS", default=10000)
VINOVA_IMPORT_MAX_COLUMNS = env.int("VINOVA_IMPORT_MAX_COLUMNS", default=100)
VINOVA_ARCHIVE_MAX_MEMBERS = env.int("VINOVA_ARCHIVE_MAX_MEMBERS", default=100000)
VINOVA_ARCHIVE_MAX_UNCOMPRESSED_MB = env.int("VINOVA_ARCHIVE_MAX_UNCOMPRESSED_MB", default=51200)
VINOVA_TRUST_PROXY_HEADERS = env.bool("VINOVA_TRUST_PROXY_HEADERS", default=False)
VINOVA_SESSION_ABSOLUTE_MINUTES = env.int("VINOVA_SESSION_ABSOLUTE_MINUTES", default=480)

LOG_LEVEL = env("LOG_LEVEL", default="INFO").upper()
DJANGO_LOG_LEVEL = env("DJANGO_LOG_LEVEL", default=LOG_LEVEL).upper()
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "filters": {"redact_sensitive": {"()": "apps.common.logging.SensitiveDataFilter"}},
    "formatters": {"json": {"()": "apps.common.logging.JsonFormatter"}},
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["redact_sensitive"],
        }
    },
    "root": {"handlers": ["console"], "level": LOG_LEVEL},
    "loggers": {
        "django": {"handlers": ["console"], "level": DJANGO_LOG_LEVEL, "propagate": False},
        "django.server": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "django.security": {"handlers": ["console"], "level": "WARNING", "propagate": False},
        "celery": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "apps.continuity": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
        "apps.api": {"handlers": ["console"], "level": LOG_LEVEL, "propagate": False},
    },
}
