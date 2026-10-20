"""ES: Este módulo implementa el componente wsgi para el dominio de configuración.

EN: This module implements the wsgi component for the configuration domain.

Contexto existente / Existing context:
Vinova runtime configuration for wsgi.
"""

import os
from django.core.wsgi import get_wsgi_application
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.production')
application = get_wsgi_application()
