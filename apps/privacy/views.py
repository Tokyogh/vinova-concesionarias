"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de privacidad.

EN: This module orchestrates HTTP requests, permissions, and responses for the privacy domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the privacy domain.
"""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.conf import settings
from django.http import FileResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.utils.http import url_has_allowed_host_and_scheme
from django.utils import timezone
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from apps.accounts.scopes import has_global_permission
from apps.accounts.views import PermissionCodeRequiredMixin
from apps.audit.services import audit_log
from apps.common.rate_limit import public_rate_limit_exceeded, public_rate_limited_response
from apps.privacy.cookies import encode_cookie_preferences, read_cookie_preferences
from apps.privacy.forms import CookiePreferencesForm, InternalDataSubjectRequestForm, PublicDataSubjectRequestForm, RequestStatusForm, RetentionPolicyForm
from apps.privacy.models import DataExportJob, DataSubjectRequest, RetentionPolicy
from apps.privacy.selectors import (
    privacy_metrics,
    scoped_consent_queryset,
    scoped_data_request_queryset,
    scoped_export_job_queryset,
    scoped_retention_policy_queryset,
)
from apps.privacy.services import anonymize_customer, create_subject_export, export_file_path, hash_text, update_request_status


class CookiePreferencesView(TemplateView):
    template_name = "privacy/public/cookie_preferences.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        current = read_cookie_preferences(self.request)
        ctx["form"] = CookiePreferencesForm(
            initial={
                "preferences": current.preferences,
                "analytics": current.analytics,
                "external_media": current.external_media,
                "action": "save",
                "next": self.request.GET.get("next", ""),
            }
        )
        ctx["current_preferences"] = current
        return ctx


class CookiePreferencesUpdateView(View):
    template_name = "privacy/public/cookie_preferences.html"

    def post(self, request):
        form = CookiePreferencesForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form}, status=400)
        selected = form.selected_categories()
        response_target = form.cleaned_data.get("next", "")
        if not url_has_allowed_host_and_scheme(
            url=response_target,
            allowed_hosts={request.get_host()},
            require_https=request.is_secure(),
        ):
            response_target = reverse_lazy("privacy_public:cookie_settings")
        response = redirect(response_target)
        response.set_cookie(
            settings.VINOVA_COOKIE_CONSENT_NAME,
            encode_cookie_preferences(**selected),
            max_age=settings.VINOVA_COOKIE_CONSENT_AGE,
            secure=settings.SESSION_COOKIE_SECURE,
            httponly=True,
            samesite="Lax",
            path="/",
        )
        return response


class PublicDataSubjectRequestView(CreateView):
    template_name = "privacy/public/request_form.html"
    form_class = PublicDataSubjectRequestForm
    success_url = reverse_lazy("privacy_public:thanks")

    def post(self, request, *args, **kwargs):
        if public_rate_limit_exceeded(request, scope="privacy-request"):
            return public_rate_limited_response()
        return super().post(request, *args, **kwargs)

    @transaction.atomic
    def form_valid(self, form):
        self.object = form.save(commit=False)
        self.object.metadata = {
            "ip_hash": hash_text(self.request.META.get("REMOTE_ADDR", "")),
            "user_agent_hash": hash_text(self.request.META.get("HTTP_USER_AGENT", "")),
        }
        self.object.save()
        audit_log(action="privacy.request.public_created", target=self.object, after={"request_type": self.object.request_type, "contact_provided": bool(self.object.requester_email or self.object.requester_phone)}, is_sensitive=True)
        return redirect(self.success_url)


class PublicDataSubjectThanksView(TemplateView):
    template_name = "privacy/public/thanks.html"


class PrivacyAccessMixin(PermissionCodeRequiredMixin):
    permission_code = "privacy.view"


class PrivacyDashboardView(PrivacyAccessMixin, TemplateView):
    template_name = "privacy/internal/dashboard.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["metrics"] = privacy_metrics(self.request.user)
        ctx["recent_requests"] = scoped_data_request_queryset(self.request.user)[:8]
        ctx["recent_consents"] = scoped_consent_queryset(self.request.user)[:8]
        ctx["policies"] = scoped_retention_policy_queryset(self.request.user)[:8]
        return ctx


class DataSubjectRequestListView(PrivacyAccessMixin, ListView):
    template_name = "privacy/internal/request_list.html"
    context_object_name = "requests_list"
    paginate_by = 25

    def get_queryset(self):
        qs = scoped_data_request_queryset(self.request.user)
        status = self.request.GET.get("status", "")
        request_type = self.request.GET.get("type", "")
        query = self.request.GET.get("q", "").strip()
        if status:
            qs = qs.filter(status=status)
        if request_type:
            qs = qs.filter(request_type=request_type)
        if query:
            from django.db.models import Q
            qs = qs.filter(Q(requester_name__icontains=query) | Q(requester_email__icontains=query) | Q(requester_phone__icontains=query) | Q(customer__first_name__icontains=query) | Q(customer__last_name__icontains=query))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["statuses"] = DataSubjectRequest.Status.choices
        ctx["types"] = DataSubjectRequest.RequestType.choices
        return ctx


class DataSubjectRequestCreateView(PrivacyAccessMixin, CreateView):
    template_name = "privacy/internal/request_form.html"
    form_class = InternalDataSubjectRequestForm

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if not request.user.has_perm_code("privacy.manage"):
            raise PermissionDenied("No tienes permiso para crear solicitudes internas.")
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        self.object = form.save()
        audit_log(user=self.request.user, action="privacy.request.created", target=self.object, customer=self.object.customer, after={"request_type": self.object.request_type}, is_sensitive=True)
        messages.success(self.request, "Solicitud registrada.")
        return redirect("privacy:request_detail", public_id=self.object.public_id)


class DataSubjectRequestDetailView(PrivacyAccessMixin, DetailView):
    template_name = "privacy/internal/request_detail.html"
    context_object_name = "data_request"
    slug_field = "public_id"
    slug_url_kwarg = "public_id"

    def get_queryset(self):
        return scoped_data_request_queryset(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["status_form"] = RequestStatusForm(initial={"status": self.object.status, "resolution": self.object.resolution, "legal_hold_reason": self.object.legal_hold_reason})
        ctx["exports"] = self.object.exports.all()
        return ctx


class DataSubjectRequestUpdateView(PrivacyAccessMixin, UpdateView):
    template_name = "privacy/internal/request_form.html"
    form_class = InternalDataSubjectRequestForm
    slug_field = "public_id"
    slug_url_kwarg = "public_id"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        if not request.user.has_perm_code("privacy.manage"):
            raise PermissionDenied("No tienes permiso para editar solicitudes.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return scoped_data_request_queryset(self.request.user, permission_code="privacy.manage")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    @transaction.atomic
    def form_valid(self, form):
        before = {field: getattr(self.object, field) for field in form.fields}
        self.object = form.save()
        audit_log(
            user=self.request.user,
            action="privacy.request.updated",
            target=self.object,
            customer=self.object.customer,
            before=before,
            after={field: getattr(self.object, field) for field in form.fields},
            is_sensitive=True,
        )
        messages.success(self.request, "Solicitud actualizada.")
        return redirect("privacy:request_detail", public_id=self.object.public_id)


class DataSubjectRequestStatusView(PrivacyAccessMixin, View):
    def post(self, request, public_id):
        if not request.user.has_perm_code("privacy.manage"):
            raise PermissionDenied("No tienes permiso para gestionar solicitudes.")
        item = get_object_or_404(
            scoped_data_request_queryset(request.user, permission_code="privacy.manage"),
            public_id=public_id,
        )
        form = RequestStatusForm(request.POST)
        if form.is_valid():
            update_request_status(actor=request.user, request_obj=item, **form.cleaned_data)
            messages.success(request, "Estado actualizado.")
        else:
            messages.error(request, "No se pudo actualizar el estado.")
        return redirect("privacy:request_detail", public_id=item.public_id)


class DataSubjectExportView(PrivacyAccessMixin, View):
    def post(self, request, public_id):
        if not request.user.has_perm_code("privacy.export"):
            raise PermissionDenied("No tienes permiso para exportar datos personales.")
        item = get_object_or_404(
            scoped_data_request_queryset(request.user, permission_code="privacy.export"),
            public_id=public_id,
        )
        try:
            job = create_subject_export(actor=request.user, request_obj=item)
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, f"Exportación generada con hash {job.sha256[:12]}…")
        return redirect("privacy:request_detail", public_id=item.public_id)


class DataExportDownloadView(PrivacyAccessMixin, View):
    def get(self, request, public_id):
        if not request.user.has_perm_code("privacy.export"):
            raise PermissionDenied("No tienes permiso para descargar exportaciones.")
        job = get_object_or_404(
            scoped_export_job_queryset(request.user, permission_code="privacy.export"),
            public_id=public_id,
            status=DataExportJob.Status.COMPLETED,
        )
        if job.expires_at and job.expires_at <= timezone.now():
            job.status = DataExportJob.Status.EXPIRED
            job.save(update_fields=["status", "updated_at"])
            messages.error(request, "La exportación expiró. Genera una nueva desde la solicitud.")
            return redirect("privacy:request_detail", public_id=job.request.public_id)
        path = export_file_path(job)
        if not path.exists():
            messages.error(request, "El archivo ya no está disponible.")
            return redirect("privacy:request_detail", public_id=job.request.public_id)
        audit_log(user=request.user, action="privacy.export.download", target=job, customer=job.customer, after={"sha256": job.sha256}, is_sensitive=True)
        return FileResponse(path.open("rb"), as_attachment=True, filename=job.filename)


class DataSubjectAnonymizeView(PrivacyAccessMixin, View):
    def post(self, request, public_id):
        if not request.user.has_perm_code("privacy.anonymize"):
            raise PermissionDenied("No tienes permiso para anonimizar datos.")
        item = get_object_or_404(
            scoped_data_request_queryset(request.user, permission_code="privacy.anonymize"),
            public_id=public_id,
        )
        try:
            record = anonymize_customer(actor=request.user, request_obj=item, notes=request.POST.get("notes", ""))
        except ValueError as exc:
            messages.error(request, str(exc))
        else:
            messages.success(request, f"Anonimización completada. Evidencia: {record.before_hash[:12]}…")
        return redirect("privacy:request_detail", public_id=item.public_id)


class ConsentListView(PrivacyAccessMixin, ListView):
    template_name = "privacy/internal/consent_list.html"
    context_object_name = "consents"
    paginate_by = 30

    def get_queryset(self):
        return scoped_consent_queryset(self.request.user)


class GlobalRetentionAccessMixin(PrivacyAccessMixin):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not has_global_permission(request.user, self.permission_code):
            raise PermissionDenied("Las políticas de retención requieren un permiso global.")
        return super().dispatch(request, *args, **kwargs)


class RetentionPolicyListView(GlobalRetentionAccessMixin, ListView):
    template_name = "privacy/internal/retention_list.html"
    context_object_name = "policies"

    def get_queryset(self):
        return scoped_retention_policy_queryset(self.request.user)


class RetentionPolicyCreateView(GlobalRetentionAccessMixin, CreateView):
    permission_code = "privacy.manage"
    template_name = "privacy/internal/retention_form.html"
    form_class = RetentionPolicyForm

    @transaction.atomic
    def form_valid(self, form):
        self.object = form.save()
        audit_log(user=self.request.user, action="privacy.retention.created", target=self.object, after={"retention_days": self.object.retention_days, "action": self.object.action})
        messages.success(self.request, "Política de retención creada.")
        return redirect("privacy:retention_list")


class RetentionPolicyUpdateView(GlobalRetentionAccessMixin, UpdateView):
    permission_code = "privacy.manage"
    template_name = "privacy/internal/retention_form.html"
    form_class = RetentionPolicyForm
    model = RetentionPolicy

    @transaction.atomic
    def form_valid(self, form):
        before = {field: getattr(self.object, field) for field in form.fields}
        self.object = form.save()
        audit_log(
            user=self.request.user,
            action="privacy.retention.updated",
            target=self.object,
            before=before,
            after={field: getattr(self.object, field) for field in form.fields},
        )
        messages.success(self.request, "Política de retención actualizada.")
        return redirect("privacy:retention_list")
