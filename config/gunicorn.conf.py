"""ES: Este módulo implementa el componente gunicorn.conf para el dominio de configuración.

EN: This module implements the gunicorn.conf component for the configuration domain.

Contexto existente / Existing context:
Vinova runtime configuration for gunicorn.conf.
"""

from __future__ import annotations

import multiprocessing
import os

bind = os.getenv("GUNICORN_BIND", "0.0.0.0:8000")
workers = int(os.getenv("GUNICORN_WORKERS", str(min(4, max(2, multiprocessing.cpu_count() * 2 + 1)))))
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "gthread")
threads = int(os.getenv("GUNICORN_THREADS", "2"))
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "1000"))
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "100"))
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")
capture_output = True
control_socket_disable = os.getenv("GUNICORN_CONTROL_SOCKET_DISABLE", "true").lower() in {"1", "true", "yes"}
preload_app = os.getenv("GUNICORN_PRELOAD", "false").lower() in {"1", "true", "yes"}
worker_tmp_dir = "/dev/shm" if os.path.isdir("/dev/shm") else None
access_log_format = (
    '{"remote":"%(h)s","method":"%(m)s","path":"%(U)s",'
    '"status":%(s)s,"bytes":%(B)s,"duration_us":%(D)s,"referer":"%(f)s","agent":"%(a)s"}'
)
