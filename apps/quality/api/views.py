"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de calidad.

EN: This module orchestrates HTTP requests, permissions, and responses for the quality domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the quality domain.
"""

from django.urls import reverse
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.authentication import SessionAuthentication
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.quality.api.serializers import (
    QualityRunCreateSerializer,
    QualityRunListSerializer,
    QualityRunSerializer,
)
from apps.quality.dispatch import enqueue_quality_run
from apps.quality.models import QualityRun
from apps.quality.permissions import CanViewQuality, SessionQualityRunnerOnly
from apps.quality.selectors import quality_run_queryset
from apps.quality.services import create_quality_run


class QualityRunListAPIView(ListAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [CanViewQuality]
    serializer_class = QualityRunListSerializer
    queryset = quality_run_queryset()


class QualityRunDetailAPIView(RetrieveAPIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [CanViewQuality]
    serializer_class = QualityRunSerializer
    lookup_field = "public_id"
    queryset = quality_run_queryset().prefetch_related("checks")


class QualityRunCreateAPIView(APIView):
    authentication_classes = [SessionAuthentication]
    permission_classes = [SessionQualityRunnerOnly]

    @extend_schema(
        request=QualityRunCreateSerializer,
        responses={
            202: QualityRunSerializer,
            409: OpenApiResponse(description="Ya existe una ejecución activa."),
            503: OpenApiResponse(description="El worker QA no está disponible."),
        },
        operation_id="quality_run_execute",
        description="Ejecuta uno de los perfiles QA cerrados mediante sesión administrativa y CSRF.",
    )
    def post(self, request):
        serializer = QualityRunCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            run = create_quality_run(
                profile=serializer.validated_data["profile"],
                trigger=QualityRun.Trigger.API,
                actor=request.user,
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_409_CONFLICT)
        dispatch = enqueue_quality_run(run)
        payload = QualityRunSerializer(dispatch.run, context={"request": request}).data
        payload["queued"] = dispatch.queued
        payload["detail_url"] = request.build_absolute_uri(
            reverse("api_v1:quality-api:run_detail", kwargs={"public_id": run.public_id})
        )
        return Response(payload, status=status.HTTP_202_ACCEPTED if dispatch.queued else status.HTTP_503_SERVICE_UNAVAILABLE)
