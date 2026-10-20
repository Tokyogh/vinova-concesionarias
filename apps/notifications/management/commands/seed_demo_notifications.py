"""ES: Implementa el comando administrativo «seed demo notifications» para notificaciones.

EN: Implements the «seed demo notifications» management command for notifications.

Contexto existente / Existing context:
Django management command for seed demo notifications.
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.accounts.models import User
from apps.customers.models import Customer
from apps.notifications.models import NotificationTemplate
from apps.notifications.services import create_notification_message
from apps.notifications.forms import NotificationMessageForm


class Command(BaseCommand):
    help = "Crea plantillas y notificaciones demo para Vinova Pro."

    @transaction.atomic
    def handle(self, *args, **options):
        actor = User.objects.filter(is_superuser=True).first() or User.objects.filter(is_staff=True).first() or User.objects.first()
        templates = [
            ("Seguimiento de cotización", NotificationTemplate.TemplateType.SALE, "Seguimiento de cotización", "Hola, te escribimos para dar seguimiento a tu cotización. Nuestro equipo puede ayudarte con disponibilidad, reserva o documentación."),
            ("Documento pendiente", NotificationTemplate.TemplateType.DOCUMENT, "Documento pendiente de revisión", "Existe un documento pendiente de revisión. Ingresa al panel o contacta al responsable para completar el proceso."),
            ("Alerta de atención", NotificationTemplate.TemplateType.CUSTOMER_SERVICE, "Atención requerida", "Un cliente requiere seguimiento. Revisa el historial, notas internas y próxima acción recomendada."),
        ]
        created_templates = []
        for name, template_type, subject, body in templates:
            template, _ = NotificationTemplate.objects.update_or_create(
                name=name,
                defaults={"template_type": template_type, "subject": subject, "body": body, "is_active": True, "created_by": actor},
            )
            created_templates.append(template)
        recipients = list(User.objects.filter(is_active=True)[:3])
        customers = list(Customer.objects.filter(is_deleted=False)[:2])
        if actor and (recipients or customers) and not actor.created_notifications.exists():
            template = created_templates[0]
            data = {
                "template": template.pk,
                "title": template.subject,
                "body": template.body,
                "message_type": "message",
                "priority": "normal",
                "recipient_users": [u.pk for u in recipients],
                "recipient_customers": [c.pk for c in customers],
            }
            form = NotificationMessageForm(data=data, user=actor)
            if form.is_valid():
                create_notification_message(actor=actor, form=form)
        self.stdout.write(self.style.SUCCESS("Notificaciones demo creadas."))
