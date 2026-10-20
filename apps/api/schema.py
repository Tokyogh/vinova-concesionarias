"""ES: Este módulo implementa el componente schema para el dominio de API e integraciones.

EN: This module implements the schema component for the api domain.

Contexto existente / Existing context:
Schema support for the api domain.
"""

from drf_spectacular.extensions import OpenApiAuthenticationExtension


class APIClientAuthenticationScheme(OpenApiAuthenticationExtension):
    target_class = "apps.api.authentication.APIClientAuthentication"
    name = "VinovaAPIKey"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "vnp_<client_id>.<secret>",
            "description": "Token empresarial de cliente API. El secreto se muestra una sola vez.",
        }
