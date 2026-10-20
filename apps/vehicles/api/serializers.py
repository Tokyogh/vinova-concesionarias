"""ES: Este módulo serializa y valida contratos de API para el dominio de vehículos.

EN: This module serializes and validates API contracts for the vehicles domain.

Contexto existente / Existing context:
REST serializers and API validation for the vehicles domain.
"""

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers
from apps.common.validators import (
    validate_nonnegative_decimal,
    validate_vehicle_identifier,
    validate_vehicle_plate,
    validate_vehicle_year,
)
from apps.vehicles.models import Vehicle, VehicleMedia, VehiclePartSpecification
from apps.vehicles.services import create_vehicle_from_data, update_vehicle_from_data


class VehicleMediaSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()

    class Meta:
        model = VehicleMedia
        fields = ["id", "media_type", "title", "alt_text", "order", "file_url"]

    def get_file_url(self, obj) -> str | None:
        return obj.resource.file.url if obj.resource.file else None


class VehiclePartSpecificationSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = VehiclePartSpecification
        fields = [
            "id",
            "part_code",
            "title",
            "summary",
            "description",
            "specs",
            "hotspot_label",
            "hotspot_x",
            "hotspot_y",
            "hotspot_z",
            "order",
            "image_url",
        ]

    def get_image_url(self, obj) -> str | None:
        return obj.image.file.url if obj.image and obj.image.file else None


class VehicleSerializer(serializers.ModelSerializer):
    """ES: Agrupa el componente «vehicle serializer» del dominio de vehículos y sus reglas relacionadas. Además, rechaza estados o entradas inválidas.

    EN: Groups the «vehicle serializer» component and its related rules in the vehicles domain. It also rejects invalid input or state.
    """

    brand_name = serializers.CharField(source="brand.name", read_only=True)
    model_name = serializers.CharField(source="model.name", read_only=True)
    media = VehicleMediaSerializer(many=True, read_only=True)
    part_specs = VehiclePartSpecificationSerializer(many=True, read_only=True)

    class Meta:
        model = Vehicle
        fields = [
            "id",
            "brand",
            "brand_name",
            "model",
            "model_name",
            "branch",
            "year",
            "version",
            "internal_code",
            "vin",
            "plate",
            "color",
            "mileage",
            "price",
            "status",
            "short_description",
            "description",
            "public_slug",
            "is_featured",
            "media",
            "part_specs",
        ]
        read_only_fields = ["internal_code", "public_slug", "media", "part_specs"]
        extra_kwargs = {
            "year": {"validators": [validate_vehicle_year]},
            "vin": {"validators": [validate_vehicle_identifier]},
            "plate": {"validators": [validate_vehicle_plate]},
            "mileage": {"min_value": 0},
            "price": {"validators": [validate_nonnegative_decimal], "min_value": 0},
        }

    def validate(self, attrs):
        brand = attrs.get("brand", getattr(self.instance, "brand", None))
        model = attrs.get("model", getattr(self.instance, "model", None))
        branch = attrs.get("branch", getattr(self.instance, "branch", None))
        if brand and model and model.brand_id != brand.pk:
            raise serializers.ValidationError({"model": "El modelo no pertenece a la marca indicada."})
        if branch and not branch.is_active:
            raise serializers.ValidationError({"branch": "La sucursal seleccionada no está activa."})
        return attrs

    def create(self, validated_data):
        try:
            return create_vehicle_from_data(
                actor=self.context["request"].user,
                validated_data=validated_data,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                exc.message_dict if hasattr(exc, "message_dict") else exc.messages
            ) from exc

    def update(self, instance, validated_data):
        try:
            return update_vehicle_from_data(
                actor=self.context["request"].user,
                vehicle=instance,
                validated_data=validated_data,
            )
        except DjangoValidationError as exc:
            raise serializers.ValidationError(
                exc.message_dict if hasattr(exc, "message_dict") else exc.messages
            ) from exc
