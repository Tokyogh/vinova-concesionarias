"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de notificaciones.

EN: This module orchestrates HTTP requests, permissions, and responses for the notifications domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the notifications domain.
"""

from __future__ import annotations

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.accounts.views import PermissionCodeRequiredMixin
from apps.notifications.forms import (
    NotificationInboxSearchForm,
    NotificationMessageForm,
    NotificationSearchForm,
    NotificationTemplateForm,
    NotificationTemplateSearchForm,
    CampaignForm,
    CampaignMessageForm,
)
from apps.notifications.models import Campaign, NotificationMessage, NotificationRecipient, NotificationTemplate
from apps.notifications.selectors import (
    campaign_detail_queryset,
    campaigns_queryset,
    notification_detail_queryset,
    notification_messages_queryset,
    notification_metrics,
    notification_templates_queryset,
    user_inbox_queryset,
)
from apps.notifications.services import (
    archive_message,
    archive_notification_template,
    archive_recipient,
    create_notification_message,
    create_notification_template,
    mark_recipient_read,
    update_notification_template,
    calculate_campaign_recipients,
    confirm_campaign,
    create_campaign,
    prepare_campaign_message,
    render_campaign_text,
)


class NotificationPermissionFallbackMixin(PermissionCodeRequiredMixin):
    permission_code = "notifications.view"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.has_perm_code("notifications.view"):
            if request.user.has_perm_code("notifications.send"):
                self.permission_code = "notifications.send"
        return super().dispatch(request, *args, **kwargs)


class InternalNotificationInboxView(NotificationPermissionFallbackMixin, ListView):
    template_name = "notifications/internal/inbox.html"
    context_object_name = "recipients"
    paginate_by = 20

    def get_queryset(self):
        self.search_form = NotificationInboxSearchForm(self.request.GET)
        query = status = ""
        if self.search_form.is_valid():
            query = self.search_form.cleaned_data.get("q", "")
            status = self.search_form.cleaned_data.get("status", "")
        return user_inbox_queryset(self.request.user, query=query, status=status)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_form"] = self.search_form
        ctx["metrics"] = notification_metrics(self.request.user)
        ctx["can_view_campaigns"] = self.request.user.has_perm_code("campaigns.view")
        return ctx


class InternalNotificationSentView(NotificationPermissionFallbackMixin, ListView):
    template_name = "notifications/internal/sent.html"
    context_object_name = "notifications"
    paginate_by = 20

    def get_queryset(self):
        self.search_form = NotificationSearchForm(self.request.GET, user=self.request.user)
        query = message_type = priority = ""
        branch = None
        if self.search_form.is_valid():
            query = self.search_form.cleaned_data.get("q", "")
            message_type = self.search_form.cleaned_data.get("message_type", "")
            priority = self.search_form.cleaned_data.get("priority", "")
            branch = self.search_form.cleaned_data.get("branch")
        permission_code = "notifications.send" if self.request.user.has_perm_code("notifications.send") else "notifications.view"
        qs = notification_messages_queryset(user=self.request.user, permission_code=permission_code, include_personal=False, query=query, message_type=message_type, priority=priority, branch=branch)
        if not self.request.user.is_superuser and not self.request.user.has_perm_code("notifications.send"):
            qs = qs.filter(recipients__user=self.request.user).distinct()
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_form"] = self.search_form
        ctx["metrics"] = notification_metrics(self.request.user)
        ctx["can_view_campaigns"] = self.request.user.has_perm_code("campaigns.view")
        return ctx


class InternalNotificationComposeView(PermissionCodeRequiredMixin, CreateView):
    permission_code = "notifications.send"
    model = NotificationMessage
    form_class = NotificationMessageForm
    template_name = "notifications/internal/message_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            self.object = create_notification_message(actor=self.request.user, form=form)
        except ValidationError as exc:
            form.add_error(None, exc.message if hasattr(exc, "message") else exc)
            return self.form_invalid(form)
        messages.success(self.request, "Notificación enviada correctamente.")
        return redirect("notifications_internal:detail", pk=self.object.pk)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["page_heading"] = "Enviar notificación"
        ctx["mode"] = "create"
        return ctx


class InternalNotificationDetailView(NotificationPermissionFallbackMixin, DetailView):
    template_name = "notifications/internal/message_detail.html"
    context_object_name = "notification"

    def get_queryset(self):
        user = self.request.user
        if user.has_perm_code("notifications.send"):
            return notification_detail_queryset(user=user)
        return notification_detail_queryset(user=user, permission_code="notifications.view").filter(recipients__user=user).distinct()

    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        user = self.request.user
        if user.is_superuser or user.has_perm_code("notifications.send") or obj.sender_id == user.id:
            return obj
        if not obj.recipients.filter(user=user).exists():
            raise PermissionDenied("No tienes permiso para ver esta notificación.")
        return obj

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        user_recipient = self.object.recipients.filter(user=self.request.user).first()
        if user_recipient and user_recipient.status == NotificationRecipient.DeliveryStatus.UNREAD:
            mark_recipient_read(actor=self.request.user, recipient=user_recipient)
        can_manage = notification_detail_queryset(user=self.request.user, include_personal=False).filter(pk=self.object.pk).exists()
        recipients = self.object.recipients.select_related("user", "customer")
        ctx["recipients"] = recipients if can_manage else recipients.filter(user=self.request.user)
        ctx["user_recipient"] = user_recipient
        return ctx


class InternalNotificationArchiveRecipientView(NotificationPermissionFallbackMixin, View):
    def post(self, request, pk):
        recipient = get_object_or_404(NotificationRecipient.objects.select_related("notification"), notification_id=pk, user=request.user)
        archive_recipient(actor=request.user, recipient=recipient)
        messages.success(request, "Mensaje archivado de tu bandeja.")
        return redirect("notifications_internal:inbox")


class InternalNotificationArchiveMessageView(PermissionCodeRequiredMixin, View):
    permission_code = "notifications.send"

    def post(self, request, pk):
        notification = get_object_or_404(notification_detail_queryset(user=request.user, include_personal=False), pk=pk)
        archive_message(actor=request.user, message=notification)
        messages.success(request, "Notificación archivada correctamente.")
        return redirect("notifications_internal:sent")


class InternalNotificationTemplateListView(PermissionCodeRequiredMixin, ListView):
    permission_code = "notifications.manage_templates"
    template_name = "notifications/internal/template_list.html"
    context_object_name = "templates"
    paginate_by = 20

    def get_queryset(self):
        self.search_form = NotificationTemplateSearchForm(self.request.GET)
        query = template_type = ""
        if self.search_form.is_valid():
            query = self.search_form.cleaned_data.get("q", "")
            template_type = self.search_form.cleaned_data.get("template_type", "")
        return notification_templates_queryset(query=query, template_type=template_type)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_form"] = self.search_form
        return ctx


class InternalNotificationTemplateCreateView(PermissionCodeRequiredMixin, CreateView):
    permission_code = "notifications.manage_templates"
    model = NotificationTemplate
    form_class = NotificationTemplateForm
    template_name = "notifications/internal/template_form.html"

    def form_valid(self, form):
        self.object = create_notification_template(actor=self.request.user, form=form)
        messages.success(self.request, "Plantilla creada correctamente.")
        return redirect("notifications_internal:templates")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["mode"] = "create"
        ctx["page_heading"] = "Crear plantilla de notificación"
        return ctx


class InternalNotificationTemplateUpdateView(PermissionCodeRequiredMixin, UpdateView):
    permission_code = "notifications.manage_templates"
    model = NotificationTemplate
    form_class = NotificationTemplateForm
    template_name = "notifications/internal/template_form.html"

    def get_queryset(self):
        return NotificationTemplate.objects.filter(is_deleted=False)

    def form_valid(self, form):
        self.object = update_notification_template(actor=self.request.user, template=self.object, form=form)
        messages.success(self.request, "Plantilla actualizada correctamente.")
        return redirect("notifications_internal:templates")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["mode"] = "update"
        ctx["page_heading"] = "Editar plantilla de notificación"
        return ctx


class InternalNotificationTemplateArchiveView(PermissionCodeRequiredMixin, View):
    permission_code = "notifications.manage_templates"

    def post(self, request, pk):
        template = get_object_or_404(NotificationTemplate.objects.filter(is_deleted=False), pk=pk)
        archive_notification_template(actor=request.user, template=template)
        messages.success(request, "Plantilla archivada correctamente.")
        return redirect(reverse("notifications_internal:templates"))


class CampaignListView(PermissionCodeRequiredMixin, ListView):
    permission_code = "campaigns.view"
    template_name = "notifications/internal/campaign_list.html"
    context_object_name = "campaigns"
    paginate_by = 20

    def get_queryset(self):
        return campaigns_queryset(user=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["can_manage"] = self.request.user.has_perm_code("campaigns.manage")
        return ctx


class CampaignCreateView(PermissionCodeRequiredMixin, CreateView):
    permission_code = "campaigns.manage"
    model = Campaign
    form_class = CampaignForm
    template_name = "notifications/internal/campaign_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        self.object = create_campaign(actor=self.request.user, form=form)
        messages.success(self.request, "Campaña creada. Calcula y revisa los destinatarios antes de preparar el mensaje.")
        return redirect("notifications_internal:campaign_detail", pk=self.object.pk)


class CampaignDetailView(PermissionCodeRequiredMixin, DetailView):
    permission_code = "campaigns.view"
    template_name = "notifications/internal/campaign_detail.html"
    context_object_name = "campaign"

    def get_queryset(self):
        return campaign_detail_queryset(user=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        snapshots = self.object.recipient_snapshots.all()
        ctx["snapshots"] = snapshots[:100]
        ctx["can_manage"] = campaigns_queryset(user=self.request.user, permission_code="campaigns.manage").filter(pk=self.object.pk).exists()
        ctx["can_send"] = campaigns_queryset(user=self.request.user, permission_code="campaigns.send").filter(pk=self.object.pk).exists()
        if self.object.status in {Campaign.Status.READY, Campaign.Status.SENT}:
            preview_recipient = snapshots.first()
            if preview_recipient:
                ctx["preview_subject"] = render_campaign_text(text=self.object.subject, campaign=self.object, customer_name=preview_recipient.display_name_snapshot)
                ctx["preview_body"] = render_campaign_text(text=self.object.body, campaign=self.object, customer_name=preview_recipient.display_name_snapshot)
        return ctx


class CampaignCalculateView(PermissionCodeRequiredMixin, View):
    permission_code = "campaigns.manage"

    def post(self, request, pk):
        campaign = get_object_or_404(campaigns_queryset(user=request.user, permission_code=self.permission_code), pk=pk)
        try:
            calculate_campaign_recipients(actor=request.user, campaign=campaign)
        except ValidationError as exc:
            messages.error(request, exc.message if hasattr(exc, "message") else exc)
        else:
            messages.success(request, "Destinatarios calculados y congelados para revisión.")
        return redirect("notifications_internal:campaign_detail", pk=pk)


class CampaignMessageView(PermissionCodeRequiredMixin, UpdateView):
    permission_code = "campaigns.manage"
    model = Campaign
    form_class = CampaignMessageForm
    template_name = "notifications/internal/campaign_message_form.html"

    def get_queryset(self):
        return campaigns_queryset(user=self.request.user, permission_code=self.permission_code).filter(status=Campaign.Status.REVIEW)

    def form_valid(self, form):
        try:
            self.object = prepare_campaign_message(actor=self.request.user, campaign=self.object, form=form)
        except ValidationError as exc:
            form.add_error(None, exc.message if hasattr(exc, "message") else exc)
            return self.form_invalid(form)
        messages.success(self.request, "Mensaje preparado. Revisa la vista previa y confirma el envío.")
        return redirect("notifications_internal:campaign_detail", pk=self.object.pk)


class CampaignConfirmView(PermissionCodeRequiredMixin, View):
    permission_code = "campaigns.send"

    def post(self, request, pk):
        campaign = get_object_or_404(campaigns_queryset(user=request.user, permission_code=self.permission_code), pk=pk)
        try:
            campaign = confirm_campaign(actor=request.user, campaign=campaign)
        except ValidationError as exc:
            messages.error(request, exc.message if hasattr(exc, "message") else exc)
        else:
            if campaign.status == Campaign.Status.CANCELLED:
                messages.warning(request, "La campaña se canceló porque ya no quedan destinatarios con consentimiento vigente.")
            else:
                messages.success(request, "Campaña confirmada y registrada.")
        return redirect("notifications_internal:campaign_detail", pk=pk)
