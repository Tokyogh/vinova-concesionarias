"""ES: Este módulo implementa el componente signals para el dominio de privacidad.

EN: This module implements the signals component for the privacy domain.

Contexto existente / Existing context:
Django signal handlers for the privacy domain.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.leads.models import Lead
from apps.privacy.services import register_lead_consent


@receiver(post_save, sender=Lead)
def capture_lead_consent(sender, instance, **kwargs):
    if instance.consent_data_processing:
        register_lead_consent(instance)
