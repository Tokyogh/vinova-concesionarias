"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de portal cliente.

EN: This module orchestrates HTTP requests, permissions, and responses for the portal domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the portal domain.
"""

from pathlib import Path

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import DetailView, FormView, ListView, TemplateView

from apps.accounts.forms import AvatarUploadForm
from apps.common.modules import OptionalModuleRequiredMixin, is_module_enabled
from apps.documents.downloads import open_private_file_or_404
from apps.documents.services import register_asset_download, register_document_download
from apps.invoices.services import ensure_invoice_pdf
from apps.portal.forms import (
    PortalCustomerProfileForm,
    PortalDocumentFilterForm,
    PortalInvoiceFilterForm,
    PortalNotificationFilterForm,
    PortalNotificationPreferenceForm,
    PortalServiceFilterForm,
    PortalVehicleRedeemForm,
    PortalVehicleSearchForm,
)
from apps.portal.selectors import (
    PortalCustomerUnavailable,
    portal_customer_for_user,
    portal_dashboard_data,
    portal_invoice_detail,
    portal_invoices_queryset,
    portal_manual_detail,
    portal_manuals_queryset,
    portal_private_document_detail,
    portal_private_documents_queryset,
    portal_notification_recipient_detail,
    portal_notifications_queryset,
    portal_vehicle_link_detail,
    portal_vehicle_links_queryset,
    portal_service_order_detail,
    portal_service_orders_queryset,
)
from apps.portal.services import update_portal_customer_profile
from apps.post_sales.models import ServiceOrder
from apps.notifications.models import CustomerNotificationPreference, NotificationRecipient
from apps.notifications.services import (
    archive_recipient,
    mark_all_customer_recipients_read,
    mark_recipient_read,
    update_customer_notification_preferences,
)
from apps.security_center.services import get_security_profile
from apps.vehicles.models import VehicleMedia
from apps.vehicles.services import redeem_link_code


class PortalCustomerRequiredMixin(LoginRequiredMixin):
    customer = None

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not request.user.has_perm_code("portal.access"):
            raise PermissionDenied("No tienes acceso al portal de clientes.")
        try:
            self.customer = portal_customer_for_user(request.user)
        except PortalCustomerUnavailable:
            return render(
                request,
                "portal/customer_unavailable.html",
                status=409,
            )
        request.portal_customer = self.customer
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["portal_customer"] = self.customer
        return context


class PortalDashboardView(PortalCustomerRequiredMixin, TemplateView):
    template_name = "portal/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(portal_dashboard_data(self.customer))
        self.request.portal_unread_notifications = context["unread_notification_count"]
        return context


class PortalProfileView(PortalCustomerRequiredMixin, FormView):
    template_name = "portal/profile.html"
    form_class = PortalCustomerProfileForm

    def get_initial(self):
        return {
            field: getattr(self.customer, field)
            for field in ("phone", "whatsapp", "address", "city", "province", "preferred_contact_method")
        }

    def form_valid(self, form):
        update_portal_customer_profile(actor=self.request.user, customer=self.customer, form=form)
        messages.success(self.request, "Tus datos de contacto fueron actualizados.")
        return redirect("portal:profile")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["avatar_form"] = AvatarUploadForm()
        return context


class PortalSettingsView(PortalCustomerRequiredMixin, FormView):
    template_name = "portal/settings.html"
    form_class = PortalNotificationPreferenceForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["instance"] = CustomerNotificationPreference.objects.filter(
            customer=self.customer
        ).first() or CustomerNotificationPreference(customer=self.customer)
        return kwargs

    def form_valid(self, form):
        update_customer_notification_preferences(actor=self.request.user, customer=self.customer, form=form)
        messages.success(self.request, "Tus preferencias de notificación fueron actualizadas.")
        return redirect("portal:settings")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["security_profile"] = get_security_profile(self.request.user)
        return context


class PortalVehicleListView(PortalCustomerRequiredMixin, ListView):
    template_name = "portal/vehicles/list.html"
    context_object_name = "vehicle_links"
    paginate_by = 12

    def get_queryset(self):
        self.search_form = PortalVehicleSearchForm(self.request.GET)
        query = self.search_form.cleaned_data.get("q", "") if self.search_form.is_valid() else ""
        return portal_vehicle_links_queryset(self.customer, query=query)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_form"] = self.search_form
        return context


class PortalVehicleDetailView(PortalCustomerRequiredMixin, DetailView):
    template_name = "portal/vehicles/detail.html"
    context_object_name = "vehicle_link"

    def get_object(self, queryset=None):
        return portal_vehicle_link_detail(customer=self.customer, link_pk=self.kwargs["pk"])

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        vehicle = self.object.vehicle
        context["gallery"] = [
            item
            for item in vehicle.media.all()
            if item.media_type in {VehicleMedia.MediaType.HERO, VehicleMedia.MediaType.IMAGE}
        ]
        context["model_3d"] = next(
            (item for item in vehicle.media.all() if item.media_type == VehicleMedia.MediaType.MODEL_3D),
            None,
        )
        context["masked_vin"] = f"••••••{vehicle.vin[-6:]}" if vehicle.vin else "No registrado"
        if is_module_enabled("post_sales"):
            vehicle_services = portal_service_orders_queryset(self.customer).filter(vehicle=vehicle)
            context["vehicle_service_history"] = list(
                vehicle_services.filter(
                    status__in=(ServiceOrder.Status.COMPLETED, ServiceOrder.Status.CANCELLED),
                )[:12]
            )
            context["vehicle_upcoming_services"] = list(
                vehicle_services.filter(
                    status__in=(ServiceOrder.Status.SCHEDULED, ServiceOrder.Status.IN_PROGRESS),
                )[:12]
            )
        else:
            context["vehicle_service_history"] = []
            context["vehicle_upcoming_services"] = []
        context["vehicle_documents"] = list(
            portal_private_documents_queryset(self.customer).filter(vehicle=vehicle)[:12]
        )
        context["vehicle_manuals"] = list(
            portal_manuals_queryset(self.customer).filter(vehicle_model_id=vehicle.model_id)[:12]
        )
        context["vehicle_invoices"] = list(portal_invoices_queryset(self.customer).filter(sale__vehicle=vehicle)[:12])
        return context


class PortalVehicleRedeemView(PortalCustomerRequiredMixin, FormView):
    template_name = "portal/vehicles/redeem.html"
    form_class = PortalVehicleRedeemForm

    def form_valid(self, form):
        try:
            link = redeem_link_code(
                actor=self.request.user,
                customer=self.customer,
                code=form.cleaned_data["code"],
            )
        except ValidationError as exc:
            form.add_error("code", exc.message if hasattr(exc, "message") else str(exc))
            return self.form_invalid(form)
        messages.success(self.request, f"{link.vehicle} se agregó a tu garaje.")
        return redirect("portal:vehicle_detail", pk=link.pk)


class PortalPostSalesRequiredMixin(OptionalModuleRequiredMixin, PortalCustomerRequiredMixin):
    module_code = "post_sales"


class PortalServiceListView(PortalPostSalesRequiredMixin, ListView):
    template_name = "portal/services/list.html"
    context_object_name = "orders"
    paginate_by = 12

    def get_queryset(self):
        self.filter_form = PortalServiceFilterForm(self.request.GET)
        filters = self.filter_form.cleaned_data if self.filter_form.is_valid() else {}
        queryset = portal_service_orders_queryset(
            self.customer,
            query=filters.get("q", ""),
            status=filters.get("status", ""),
        )
        self.portal_service_view = self.request.GET.get("view", "")
        if self.portal_service_view == "history" and not filters.get("status"):
            queryset = queryset.filter(
                status__in=(ServiceOrder.Status.COMPLETED, ServiceOrder.Status.CANCELLED),
            )
        elif self.portal_service_view == "upcoming" and not filters.get("status"):
            queryset = queryset.filter(
                status__in=(ServiceOrder.Status.SCHEDULED, ServiceOrder.Status.IN_PROGRESS),
            ).order_by("scheduled_at", "created_at")
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.filter_form
        context["service_view"] = self.portal_service_view
        return context


class PortalServiceDetailView(PortalPostSalesRequiredMixin, DetailView):
    template_name = "portal/services/detail.html"
    context_object_name = "service_order"

    def get_object(self, queryset=None):
        return portal_service_order_detail(customer=self.customer, order_pk=self.kwargs["pk"])


class PortalDocumentListView(PortalCustomerRequiredMixin, ListView):
    template_name = "portal/documents/list.html"
    context_object_name = "documents"
    paginate_by = 12

    def get_queryset(self):
        self.filter_form = PortalDocumentFilterForm(self.request.GET)
        filters = self.filter_form.cleaned_data if self.filter_form.is_valid() else {}
        return portal_private_documents_queryset(
            self.customer,
            query=filters.get("q", ""),
            document_type=filters.get("document_type", ""),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["manuals"] = portal_manuals_queryset(self.customer)
        context["filter_form"] = self.filter_form
        return context


class PortalPrivateDocumentDetailView(PortalCustomerRequiredMixin, DetailView):
    template_name = "portal/documents/detail.html"
    context_object_name = "document"

    def get_object(self, queryset=None):
        return portal_private_document_detail(customer=self.customer, document_pk=self.kwargs["pk"])


class PortalPrivateDocumentDownloadView(PortalCustomerRequiredMixin, View):
    def get(self, request, pk):
        document = portal_private_document_detail(customer=self.customer, document_pk=pk)
        if not document.file:
            raise Http404("El documento no tiene archivo asociado.")
        handle = open_private_file_or_404(document.file, context="documento privado del portal")
        register_document_download(actor=request.user, document=document, customer=self.customer)
        filename = document.original_name or Path(document.file.name).name
        response = FileResponse(handle, as_attachment=True, filename=filename)
        if document.mime_type:
            response["Content-Type"] = document.mime_type
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response


class PortalManualDownloadView(PortalCustomerRequiredMixin, View):
    def get(self, request, pk):
        manual = portal_manual_detail(customer=self.customer, asset_pk=pk)
        if not manual.file:
            raise Http404("El manual no tiene archivo asociado.")
        handle = open_private_file_or_404(manual.file, context="manual privado del portal")
        register_asset_download(actor=request.user, asset=manual, customer=self.customer)
        filename = manual.original_name or Path(manual.file.name).name
        response = FileResponse(handle, as_attachment=True, filename=filename)
        if manual.mime_type:
            response["Content-Type"] = manual.mime_type
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response


class PortalInvoiceListView(PortalCustomerRequiredMixin, ListView):
    template_name = "portal/invoices/list.html"
    context_object_name = "invoices"
    paginate_by = 12

    def get_queryset(self):
        self.filter_form = PortalInvoiceFilterForm(self.request.GET)
        filters = self.filter_form.cleaned_data if self.filter_form.is_valid() else {}
        return portal_invoices_queryset(
            self.customer,
            query=filters.get("q", ""),
            status=filters.get("status", ""),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.filter_form
        return context


class PortalInvoiceDetailView(PortalCustomerRequiredMixin, DetailView):
    template_name = "portal/invoices/detail.html"
    context_object_name = "invoice"

    def get_object(self, queryset=None):
        return portal_invoice_detail(customer=self.customer, invoice_pk=self.kwargs["pk"])


class PortalInvoiceDownloadView(PortalCustomerRequiredMixin, View):
    def get(self, request, pk):
        invoice = portal_invoice_detail(customer=self.customer, invoice_pk=pk)
        document = ensure_invoice_pdf(actor=request.user, invoice=invoice, customer=self.customer)
        handle = open_private_file_or_404(document.file, context="PDF de factura del portal")
        register_document_download(actor=request.user, document=document, customer=self.customer)
        filename = document.original_name or Path(document.file.name).name
        response = FileResponse(handle, as_attachment=True, filename=filename)
        response["Content-Type"] = "application/pdf"
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response


class PortalNotificationListView(PortalCustomerRequiredMixin, ListView):
    template_name = "portal/notifications/list.html"
    context_object_name = "recipients"
    paginate_by = 15

    def get_queryset(self):
        self.filter_form = PortalNotificationFilterForm(self.request.GET)
        filters = self.filter_form.cleaned_data if self.filter_form.is_valid() else {}
        return portal_notifications_queryset(
            self.customer,
            query=filters.get("q", ""),
            message_type=filters.get("message_type", ""),
            delivery_status=filters.get("delivery_status", ""),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.filter_form
        return context


class PortalNotificationDetailView(PortalCustomerRequiredMixin, DetailView):
    template_name = "portal/notifications/detail.html"
    context_object_name = "recipient"

    def get_object(self, queryset=None):
        recipient = portal_notification_recipient_detail(
            customer=self.customer,
            recipient_pk=self.kwargs["pk"],
        )
        if recipient.status == NotificationRecipient.DeliveryStatus.UNREAD:
            mark_recipient_read(actor=self.request.user, recipient=recipient)
        return recipient


class PortalNotificationArchiveView(PortalCustomerRequiredMixin, View):
    def post(self, request, pk):
        recipient = portal_notification_recipient_detail(customer=self.customer, recipient_pk=pk)
        archive_recipient(actor=request.user, recipient=recipient)
        messages.success(request, "Notificación archivada.")
        return redirect("portal:notification_list")


class PortalNotificationReadAllView(PortalCustomerRequiredMixin, View):
    def post(self, request):
        updated = mark_all_customer_recipients_read(actor=request.user, customer=self.customer)
        if updated:
            messages.success(request, f"Se marcaron {updated} notificaciones como leídas.")
        return redirect("portal:notification_list")
