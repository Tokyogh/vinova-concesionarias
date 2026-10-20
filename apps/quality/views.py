"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de calidad.

EN: This module orchestrates HTTP requests, permissions, and responses for the quality domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the quality domain.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView, ListView

from apps.audit.services import audit_log
from apps.quality.dispatch import enqueue_quality_run
from apps.quality.models import QualityRun
from apps.quality.permissions import can_run_quality, can_view_quality
from apps.quality.selectors import quality_run_queryset
from apps.quality.services import create_quality_run, quality_report_path


class QualityAccessMixin(LoginRequiredMixin):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not can_view_quality(request.user):
            raise PermissionDenied("No tienes permiso para consultar validaciones QA.")
        return super().dispatch(request, *args, **kwargs)


class QualityRunListView(QualityAccessMixin, ListView):
    template_name = "quality/internal/run_list.html"
    context_object_name = "runs"
    paginate_by = 20

    def get_queryset(self):
        queryset = quality_run_queryset()
        profile = self.request.GET.get("profile", "")
        status = self.request.GET.get("status", "")
        if profile in QualityRun.Profile.values:
            queryset = queryset.filter(profile=profile)
        if status in QualityRun.Status.values:
            queryset = queryset.filter(status=status)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(
            {
                "profiles": QualityRun.Profile.choices,
                "statuses": QualityRun.Status.choices,
                "selected_profile": self.request.GET.get("profile", ""),
                "selected_status": self.request.GET.get("status", ""),
                "can_run_quality": can_run_quality(self.request.user),
                "qa_execution_enabled": settings.VINOVA_QA_EXECUTION_ENABLED,
                "qa_automated_enabled": settings.VINOVA_QA_AUTOMATED_ENABLED,
                "qa_environment": settings.VINOVA_QA_ENVIRONMENT,
            }
        )
        return context


class QualityRunCreateView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        if not can_run_quality(request.user):
            raise PermissionDenied("No tienes permiso para ejecutar validaciones QA.")
        profile = request.POST.get("profile", "")
        try:
            run = create_quality_run(profile=profile, trigger=QualityRun.Trigger.PANEL, actor=request.user)
        except ValueError as exc:
            messages.error(request, str(exc))
            return redirect("quality:run_list")
        result = enqueue_quality_run(run)
        if result.queued:
            messages.success(request, result.message)
        else:
            messages.error(request, result.message)
        return redirect("quality:run_detail", public_id=run.public_id)


class QualityRunDetailView(QualityAccessMixin, DetailView):
    template_name = "quality/internal/run_detail.html"
    context_object_name = "run"
    slug_field = "public_id"
    slug_url_kwarg = "public_id"

    def get_queryset(self):
        return quality_run_queryset().prefetch_related("checks")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["can_run_quality"] = can_run_quality(self.request.user)
        return context


class QualityReportDownloadView(QualityAccessMixin, View):
    def get(self, request, public_id, report_format, *args, **kwargs):
        if report_format not in {"json", "html", "e2e"}:
            raise Http404("Formato no válido.")
        run = get_object_or_404(QualityRun, public_id=public_id)
        try:
            path = quality_report_path(run, report_format)
        except FileNotFoundError as exc:
            raise Http404(str(exc)) from exc
        content_type = {"json": "application/json", "html": "text/html; charset=utf-8", "e2e": "application/zip"}[report_format]
        response = FileResponse(path.open("rb"), content_type=content_type, as_attachment=True, filename=path.name)
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, no-store"
        response["Content-Security-Policy"] = "sandbox; default-src 'none'"
        audit_log(
            user=request.user,
            action="quality.report.downloaded",
            target=run,
            after={"format": report_format, "profile": run.profile, "status": run.status},
        )
        return response
