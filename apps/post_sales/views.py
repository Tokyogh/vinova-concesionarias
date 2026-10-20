"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de postventa.

EN: This module orchestrates HTTP requests, permissions, and responses for the post sales domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the post sales domain.
"""

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from apps.accounts.views import PermissionCodeRequiredMixin
from apps.common.modules import OptionalModuleRequiredMixin
from apps.post_sales.forms import ServiceOrderForm, ServiceOrderLineForm, ServiceOrderOperationalForm, ServiceOrderSearchForm, ServiceOrderStatusForm
from apps.post_sales.models import ServiceOrder
from apps.post_sales.selectors import service_order_detail_queryset, service_order_metrics, service_orders_queryset
from apps.post_sales.services import add_service_order_line, create_service_order, transition_service_order, update_service_order_operational_details


class PostSalesAccessMixin(OptionalModuleRequiredMixin, PermissionCodeRequiredMixin):
    module_code = "post_sales"
    permission_code = "post_sales.view"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and request.user.has_perm_code("post_sales.manage"):
            self.permission_code = "post_sales.manage"
        return super().dispatch(request, *args, **kwargs)


class ServiceOrderListView(PostSalesAccessMixin, ListView):
    template_name = "post_sales/order_list.html"
    context_object_name = "orders"
    paginate_by = 25

    def get_queryset(self):
        self.search_form = ServiceOrderSearchForm(self.request.GET)
        self.search_form.is_valid()
        data = self.search_form.cleaned_data
        return service_orders_queryset(self.request.user, status=data.get("status", ""), query=data.get("q", ""))

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["search_form"] = self.search_form
        context["metrics"] = service_order_metrics(self.request.user)
        return context


class ServiceOrderDetailView(PostSalesAccessMixin, DetailView):
    template_name = "post_sales/order_detail.html"
    context_object_name = "order"

    def get_queryset(self):
        return service_order_detail_queryset(self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["status_form"] = ServiceOrderStatusForm()
        context["line_form"] = ServiceOrderLineForm(user=self.request.user)
        context["operational_form"] = ServiceOrderOperationalForm(instance=self.object)
        context["can_manage"] = self.request.user.has_perm_code("post_sales.manage", self.object.branch)
        return context


class ServiceOrderCreateView(OptionalModuleRequiredMixin, PermissionCodeRequiredMixin, CreateView):
    module_code = "post_sales"
    permission_code = "post_sales.manage"
    model = ServiceOrder
    form_class = ServiceOrderForm
    template_name = "post_sales/order_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        self.object = create_service_order(actor=self.request.user, form=form)
        messages.success(self.request, "Orden de postventa creada.")
        return redirect("post_sales:detail", pk=self.object.pk)


class ServiceOrderStatusView(OptionalModuleRequiredMixin, PermissionCodeRequiredMixin, View):
    module_code = "post_sales"
    permission_code = "post_sales.manage"

    def post(self, request, pk):
        form = ServiceOrderStatusForm(request.POST)
        order = get_object_or_404(service_order_detail_queryset(request.user), pk=pk)
        if not form.is_valid():
            messages.error(request, "Estado inválido.")
            return redirect("post_sales:detail", pk=order.pk)
        try:
            transition_service_order(
                actor=request.user,
                order_id=order.pk,
                new_status=form.cleaned_data["status"],
                note=form.cleaned_data["note"],
            )
        except ValidationError as exc:
            messages.error(request, "; ".join(exc.messages))
        else:
            messages.success(request, "Estado actualizado.")
        return redirect("post_sales:detail", pk=order.pk)


class ServiceOrderLineCreateView(OptionalModuleRequiredMixin, PermissionCodeRequiredMixin, View):
    module_code = "post_sales"
    permission_code = "post_sales.manage"

    def post(self, request, pk):
        order = get_object_or_404(service_order_detail_queryset(request.user), pk=pk)
        form = ServiceOrderLineForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                add_service_order_line(actor=request.user, order_id=order.pk, form=form)
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
            else:
                messages.success(request, "Servicio agregado.")
        else:
            messages.error(request, "Revisa los datos del servicio.")
        return redirect("post_sales:detail", pk=order.pk)


class ServiceOrderOperationalUpdateView(OptionalModuleRequiredMixin, PermissionCodeRequiredMixin, View):
    module_code = "post_sales"
    permission_code = "post_sales.manage"

    def post(self, request, pk):
        order = get_object_or_404(service_order_detail_queryset(request.user), pk=pk)
        form = ServiceOrderOperationalForm(request.POST, instance=order)
        if form.is_valid():
            try:
                update_service_order_operational_details(actor=request.user, order_id=order.pk, form=form)
            except ValidationError as exc:
                messages.error(request, "; ".join(exc.messages))
            else:
                messages.success(request, "Datos de recepción y recomendación actualizados.")
        else:
            messages.error(request, "Revisa kilometrajes, diagnóstico y próxima atención.")
        return redirect("post_sales:detail", pk=order.pk)
