"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de continuidad.

EN: This module orchestrates HTTP requests, permissions, and responses for the continuity domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the continuity domain.
"""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import DetailView, ListView, TemplateView, UpdateView

from apps.accounts.scopes import has_global_permission
from apps.accounts.views import PermissionCodeRequiredMixin
from apps.audit.services import audit_log
from apps.continuity.forms import BackupCreateForm, BackupPolicyForm, RestoreDrillForm, RestoreDrillResultForm
from apps.continuity.models import BackupPolicy, BackupRecord, RestoreDrill
from apps.continuity.selectors import continuity_metrics
from apps.continuity.services import (
    backup_archive_path,
    complete_restore_drill,
    create_backup_record,
    create_restore_drill,
    update_backup_policy,
    verify_backup,
)
from apps.continuity.update_center import update_center_context
from apps.continuity.dispatch import enqueue_backup


class ContinuityAccessMixin(PermissionCodeRequiredMixin):
    permission_code = "continuity.view"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not has_global_permission(request.user, self.permission_code):
            raise PermissionDenied("Esta operación de continuidad requiere un permiso global.")
        return super().dispatch(request, *args, **kwargs)


class ContinuityDashboardView(ContinuityAccessMixin, TemplateView):
    template_name = "continuity/internal/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["metrics"] = continuity_metrics()
        ctx["backup_form"] = BackupCreateForm()
        ctx["restore_form"] = RestoreDrillForm()
        ctx["recent_backups"] = BackupRecord.objects.select_related("initiated_by").all()[:8]
        ctx["recent_drills"] = RestoreDrill.objects.select_related("backup", "performed_by").all()[:8]
        ctx["policy"] = BackupPolicy.objects.filter(is_active=True).first()
        return ctx


class UpdateCenterView(ContinuityAccessMixin, TemplateView):
    template_name = "continuity/internal/update_center.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(update_center_context())
        return context


class BackupListView(ContinuityAccessMixin, ListView):
    template_name = "continuity/internal/backup_list.html"
    context_object_name = "backups"
    paginate_by = 25
    queryset = BackupRecord.objects.select_related("initiated_by", "verified_by", "policy")


class BackupDetailView(ContinuityAccessMixin, DetailView):
    template_name = "continuity/internal/backup_detail.html"
    context_object_name = "backup"
    slug_field = "public_id"
    slug_url_kwarg = "public_id"
    queryset = BackupRecord.objects.select_related("initiated_by", "verified_by", "policy")


class BackupCreateView(ContinuityAccessMixin, View):
    permission_code = "continuity.manage"

    def post(self, request):
        form = BackupCreateForm(request.POST)
        if not form.is_valid():
            messages.error(request, "Revisa los datos del backup.")
            return redirect("continuity:dashboard")
        record = create_backup_record(
            actor=request.user,
            backup_type=form.cleaned_data["backup_type"],
            notes=form.cleaned_data["notes"],
        )
        result = enqueue_backup(record)
        if result.queued:
            messages.success(request, "Backup en cola. Celery Worker actualizará el estado al comenzar.")
        elif result.used_sync_fallback and result.record.status == BackupRecord.Status.FAILED:
            messages.error(request, f"El fallback síncrono falló: {result.record.error_message}")
        elif result.used_sync_fallback:
            messages.warning(request, "Celery no respondió; se usó el fallback síncrono permitido por este entorno.")
        else:
            messages.error(request, "No se pudo encolar el backup. Revisa Redis y Celery Worker.")
        return redirect("continuity:backup_detail", public_id=record.public_id)


class BackupVerifyView(ContinuityAccessMixin, View):
    permission_code = "continuity.manage"

    def post(self, request, public_id):
        record = get_object_or_404(BackupRecord, public_id=public_id)
        result = verify_backup(record, actor=request.user)
        messages.success(request, "Backup íntegro y verificado.") if result["valid"] else messages.error(
            request, result["reason"]
        )
        return redirect("continuity:backup_detail", public_id=record.public_id)


class BackupDownloadView(ContinuityAccessMixin, View):
    permission_code = "continuity.manage"

    def get(self, request, public_id):
        record = get_object_or_404(
            BackupRecord, public_id=public_id, status__in=[BackupRecord.Status.COMPLETED, BackupRecord.Status.VERIFIED]
        )
        path = backup_archive_path(record)
        if not path.exists():
            messages.error(request, "El archivo de backup no está disponible.")
            return redirect("continuity:backup_detail", public_id=record.public_id)
        audit_log(
            user=request.user,
            action="continuity.backup.download",
            target=record,
            after={"sha256": record.sha256, "size_bytes": record.size_bytes},
            is_sensitive=True,
        )
        return FileResponse(path.open("rb"), as_attachment=True, filename=record.filename)


class BackupPolicyUpdateView(ContinuityAccessMixin, UpdateView):
    permission_code = "continuity.manage"
    template_name = "continuity/internal/policy_form.html"
    form_class = BackupPolicyForm

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not has_global_permission(request.user, self.permission_code):
            return super().dispatch(request, *args, **kwargs)
        self.object, _ = BackupPolicy.objects.get_or_create(name="Política principal")
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        return self.object

    def form_valid(self, form):
        self.object = update_backup_policy(
            actor=self.request.user,
            policy=self.object,
            values=form.cleaned_data,
        )
        messages.success(self.request, "Política de backup actualizada.")
        return redirect("continuity:dashboard")


class RestoreDrillCreateView(ContinuityAccessMixin, View):
    permission_code = "continuity.restore"

    def post(self, request):
        form = RestoreDrillForm(request.POST)
        if form.is_valid():
            drill = create_restore_drill(actor=request.user, **form.cleaned_data)
            messages.success(request, "Simulacro creado. La restauración real debe hacerse en un entorno aislado.")
            return redirect("continuity:restore_detail", public_id=drill.public_id)
        messages.error(request, "No se pudo crear el simulacro.")
        return redirect("continuity:dashboard")


class RestoreDrillDetailView(ContinuityAccessMixin, DetailView):
    template_name = "continuity/internal/restore_detail.html"
    context_object_name = "drill"
    slug_field = "public_id"
    slug_url_kwarg = "public_id"
    queryset = RestoreDrill.objects.select_related("backup", "performed_by")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["result_form"] = RestoreDrillResultForm(instance=self.object)
        return ctx


class RestoreDrillCompleteView(ContinuityAccessMixin, View):
    permission_code = "continuity.restore"

    def post(self, request, public_id):
        drill = get_object_or_404(RestoreDrill, public_id=public_id)
        form = RestoreDrillResultForm(request.POST, instance=drill)
        if form.is_valid():
            complete_restore_drill(
                actor=request.user,
                drill=drill,
                status=form.cleaned_data["status"],
                result_summary=form.cleaned_data["result_summary"],
            )
            messages.success(request, "Resultado del simulacro registrado.")
        else:
            messages.error(request, "Revisa el resultado del simulacro.")
        return redirect("continuity:restore_detail", public_id=drill.public_id)
