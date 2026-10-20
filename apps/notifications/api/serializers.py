"""ES: Este módulo serializa y valida contratos de API para el dominio de notificaciones.

EN: This module serializes and validates API contracts for the notifications domain.

Contexto existente / Existing context:
REST serializers and API validation for the notifications domain.
"""

from rest_framework import serializers

from apps.notifications.models import NotificationMessage, NotificationRecipient, NotificationTemplate


class NotificationTemplateSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True)

    class Meta:
        model = NotificationTemplate
        fields = ["id", "name", "template_type", "subject", "body", "is_active", "created_by", "created_by_name", "created_at", "updated_at"]
        read_only_fields = ["created_by"]


class NotificationRecipientSerializer(serializers.ModelSerializer):
    user_name = serializers.CharField(source="user.get_full_name", read_only=True)
    customer_name = serializers.CharField(source="customer.display_name", read_only=True)

    class Meta:
        model = NotificationRecipient
        fields = ["id", "notification", "recipient_type", "user", "user_name", "customer", "customer_name", "display_name_snapshot", "email_snapshot", "status", "read_at", "archived_at", "created_at", "updated_at"]
        read_only_fields = ["read_at", "archived_at"]


class NotificationMessageSerializer(serializers.ModelSerializer):
    sender_name = serializers.CharField(source="sender.get_full_name", read_only=True)
    branch_name = serializers.CharField(source="branch.name", read_only=True)
    customer_name = serializers.CharField(source="related_customer.display_name", read_only=True)
    vehicle_label = serializers.SerializerMethodField()
    sale_number = serializers.CharField(source="related_sale.number", read_only=True)
    recipient_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = NotificationMessage
        fields = [
            "id", "title", "body", "message_type", "priority", "status", "sender", "sender_name", "template", "branch", "branch_name", "related_customer", "customer_name", "related_vehicle", "vehicle_label", "related_sale", "sale_number", "related_document", "sent_at", "recipient_count", "created_by", "created_at", "updated_at",
        ]
        read_only_fields = ["sender", "created_by", "sent_at"]

    def get_vehicle_label(self, obj) -> str:
        return str(obj.related_vehicle) if obj.related_vehicle else ""
