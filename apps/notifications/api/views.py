"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de notificaciones.

EN: This module orchestrates HTTP requests, permissions, and responses for the notifications domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the notifications domain.
"""

from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.permissions import BasePermission
from rest_framework.response import Response

from apps.notifications.api.serializers import NotificationMessageSerializer, NotificationRecipientSerializer, NotificationTemplateSerializer
from apps.notifications.models import NotificationMessage, NotificationRecipient, NotificationTemplate
from apps.notifications.selectors import notification_messages_queryset, notification_metrics
from apps.notifications.services import mark_recipient_read


class NotificationPermission(BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.method in {"GET", "HEAD", "OPTIONS"}:
            return request.user.has_perm_code("notifications.view") or request.user.has_perm_code("notifications.send")
        if view.basename == "notification-templates":
            return request.user.has_perm_code("notifications.manage_templates")
        return request.user.has_perm_code("notifications.send")


class NotificationMessageViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = NotificationMessageSerializer
    permission_classes = [NotificationPermission]
    queryset = NotificationMessage.objects.filter(is_deleted=False).select_related("sender", "branch", "related_customer", "related_vehicle", "related_sale", "related_document")
    filterset_fields = ["message_type", "priority", "status", "branch", "sender"]
    search_fields = ["title", "body", "sender__email", "related_customer__first_name", "related_customer__last_name", "related_customer__business_name", "related_vehicle__vin", "related_vehicle__plate", "related_sale__number"]
    ordering_fields = ["sent_at", "created_at", "priority"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not getattr(self.request.user, "is_authenticated", False):
            return self.queryset.none()
        user = self.request.user
        permission_code = "notifications.send" if user.has_perm_code("notifications.send") else "notifications.view"
        qs = notification_messages_queryset(user=user, permission_code=permission_code, include_personal=False)
        if not user.is_superuser and not user.has_perm_code("notifications.send"):
            qs = qs.filter(recipients__user=user).distinct()
        return qs

    @action(detail=False, methods=["get"], url_path="metrics")
    def metrics(self, request):
        return Response(notification_metrics(request.user))


class NotificationRecipientViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = NotificationRecipient.objects.none()
    serializer_class = NotificationRecipientSerializer
    permission_classes = [NotificationPermission]
    filterset_fields = ["recipient_type", "status", "user", "customer"]
    search_fields = ["notification__title", "display_name_snapshot", "email_snapshot"]
    ordering_fields = ["created_at", "read_at"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False) or not getattr(self.request.user, "is_authenticated", False):
            return self.queryset
        qs = NotificationRecipient.objects.select_related("notification", "user", "customer")
        user = self.request.user
        if user.is_superuser:
            return qs
        if user.has_perm_code("notifications.send"):
            return qs.filter(notification_id__in=notification_messages_queryset(user=user, include_personal=False).values("pk"))
        return qs.filter(user=user)

    @action(detail=True, methods=["post"], url_path="mark-read")
    def mark_read(self, request, pk=None):
        recipient = self.get_object()
        if recipient.user_id != request.user.id:
            from rest_framework.exceptions import PermissionDenied

            raise PermissionDenied("Solo el destinatario puede marcar la notificación como leída.")
        mark_recipient_read(actor=request.user, recipient=recipient)
        return Response(self.get_serializer(recipient).data)


class NotificationTemplateViewSet(viewsets.ModelViewSet):
    serializer_class = NotificationTemplateSerializer
    permission_classes = [NotificationPermission]
    queryset = NotificationTemplate.objects.filter(is_deleted=False)
    filterset_fields = ["template_type", "is_active"]
    search_fields = ["name", "subject", "body"]
    ordering_fields = ["name", "created_at"]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
