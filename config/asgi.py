"""ES: Este módulo implementa el componente asgi para el dominio de configuración.

EN: This module implements the asgi component for the configuration domain.

Contexto existente / Existing context:
Vinova runtime configuration for asgi.
"""

import os
from django.core.asgi import get_asgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
application = get_asgi_application()
