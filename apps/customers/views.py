"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de clientes.

EN: This module orchestrates HTTP requests, permissions, and responses for the customers domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the customers domain.
"""

from __future__ import annotations

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from apps.accounts.client_services import create_staff_client_invitation, send_client_access_email
from apps.accounts.views import PermissionCodeRequiredMixin
from apps.common.http import safe_next_url
from apps.customers.forms import CustomerAccountLinkForm, CustomerForm, CustomerNoteForm, CustomerSearchForm, CustomerVehicleInterestForm
from apps.customers.models import Customer
from apps.customers.selectors import customer_detail_queryset, customer_garage_queryset, customer_interests_queryset, customer_list_queryset, customer_metrics, customer_notes_queryset
from apps.customers.services import activate_customer, add_customer_note, add_vehicle_interest, archive_customer, create_customer, link_customer_account, update_customer


class CustomerPermissionFallbackMixin(PermissionCodeRequiredMixin):
    permission_code = "customers.view"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.has_perm_code("customers.view") and request.user.has_perm_code("customers.manage"):
            self.permission_code = "customers.manage"
        return super().dispatch(request, *args, **kwargs)


def _warn_fuzzy_identification(request, form) -> None:
    candidates = getattr(form, "fuzzy_candidates", None) or []
    if candidates:
        names = ", ".join(candidate.display_name for candidate in candidates[:3])
        messages.warning(
            request,
            f"Posibles clientes duplicados con identificación similar: {names}. Verifica antes de continuar.",
        )


class InternalCustomerListView(CustomerPermissionFallbackMixin, ListView):
    template_name = "customers/internal/customer_list.html"
    context_object_name = "customers"
    paginate_by = 20

    def get_queryset(self):
        self.search_form = CustomerSearchForm(self.request.GET, user=self.request.user)
        query = status = customer_type = sort = ""
        branch = None
        if self.search_form.is_valid():
            query = self.search_form.cleaned_data.get("q", "")
            status = self.search_form.cleaned_data.get("status", "")
            customer_type = self.search_form.cleaned_data.get("customer_type", "")
            branch = self.search_form.cleaned_data.get("branch")
            sort = self.search_form.cleaned_data.get("sort", "")
        return customer_list_queryset(
            user=self.request.user,
            query=query,
            status=status,
            customer_type=customer_type,
            branch=branch,
            sort=sort,
            identification=self.search_form.cleaned_data.get("identification", ""),
            first_name=self.search_form.cleaned_data.get("first_name", ""),
            last_name=self.search_form.cleaned_data.get("last_name", ""),
            email=self.search_form.cleaned_data.get("email", ""),
            phone=self.search_form.cleaned_data.get("phone", ""),
            plate=self.search_form.cleaned_data.get("plate", ""),
            vin=self.search_form.cleaned_data.get("vin", ""),
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_form"] = self.search_form
        ctx["metrics"] = customer_metrics(user=self.request.user)
        return ctx


class InternalCustomerCreateView(PermissionCodeRequiredMixin, CreateView):
    permission_code = "customers.manage"
    model = Customer
    form_class = CustomerForm
    template_name = "customers/internal/customer_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        self.object = create_customer(actor=self.request.user, form=form)
        _warn_fuzzy_identification(self.request, form)
        messages.success(self.request, "Cliente creado correctamente.")
        return redirect("customers_internal:detail", pk=self.object.pk)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["mode"] = "create"
        ctx["page_heading"] = "Crear cliente"
        return ctx


class InternalCustomerDetailView(CustomerPermissionFallbackMixin, DetailView):
    template_name = "customers/internal/customer_detail.html"
    context_object_name = "customer"

    def get_queryset(self):
        return customer_detail_queryset(user=self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["note_form"] = CustomerNoteForm()
        ctx["interest_form"] = CustomerVehicleInterestForm(user=self.request.user)
        ctx["account_link_form"] = CustomerAccountLinkForm(instance=self.object)
        ctx["notes"] = customer_notes_queryset(self.object)[:12]
        ctx["interests"] = customer_interests_queryset(self.object)[:12]
        ctx["garage"] = customer_garage_queryset(self.object)
        ctx["can_manage_garage"] = self.request.user.has_perm_code("vehicles.link_codes")
        return ctx


class InternalCustomerLinkAccountView(PermissionCodeRequiredMixin, View):
    permission_code = "customers.manage"

    def post(self, request, pk):
        customer = get_object_or_404(
            customer_detail_queryset(user=request.user, permission_codes=("customers.manage",)),
            pk=pk,
        )
        form = CustomerAccountLinkForm(request.POST, instance=customer)
        if form.is_valid():
            try:
                link_customer_account(actor=request.user, customer=customer, user=form.cleaned_data["account"])
            except ValidationError as exc:
                messages.error(request, exc.message if hasattr(exc, "message") else str(exc))
            else:
                messages.success(request, "Cuenta de acceso vinculada al expediente.")
        else:
            messages.error(request, "No se pudo vincular la cuenta. Revisa los datos.")
        return redirect("customers_internal:detail", pk=customer.pk)


class InternalCustomerInviteAccountView(PermissionCodeRequiredMixin, View):
    permission_code = "customers.manage"

    def post(self, request, pk):
        customer = get_object_or_404(
            customer_detail_queryset(user=request.user, permission_codes=("customers.manage",)),
            pk=pk,
        )
        try:
            invitation, raw_token = create_staff_client_invitation(actor=request.user, customer=customer)
        except ValidationError as exc:
            messages.error(request, exc.message if hasattr(exc, "message") else str(exc))
        else:
            accept_url = request.build_absolute_uri(
                reverse("accounts:client_invitation_accept", kwargs={"token": raw_token})
            )
            delivered = send_client_access_email(
                invitation=invitation,
                raw_token=raw_token,
                accept_url=accept_url,
            )
            if delivered:
                messages.success(request, "Invitación enviada al correo del cliente.")
            else:
                messages.warning(
                    request,
                    "La invitación fue creada, pero el correo no pudo entregarse. Revisa la configuración de email.",
                )
        return redirect("customers_internal:detail", pk=customer.pk)


class InternalCustomerUpdateView(PermissionCodeRequiredMixin, DetailView):
    permission_code = "customers.manage"
    template_name = "customers/internal/customer_form.html"
    context_object_name = "customer"

    def get_queryset(self):
        return customer_detail_queryset(user=self.request.user)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = CustomerForm(instance=self.object, user=request.user)
        return self.render_to_response(self.get_context_data(form=form, mode="update", page_heading="Editar cliente"))

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = CustomerForm(request.POST, instance=self.object, user=request.user)
        if form.is_valid():
            self.object = update_customer(actor=request.user, customer=self.object, form=form)
            _warn_fuzzy_identification(request, form)
            messages.success(request, "Cliente actualizado correctamente.")
            return redirect("customers_internal:detail", pk=self.object.pk)
        return self.render_to_response(self.get_context_data(form=form, mode="update", page_heading="Editar cliente"))


class InternalCustomerStatusView(PermissionCodeRequiredMixin, View):
    permission_code = "customers.manage"

    def post(self, request, pk, action):
        customer = get_object_or_404(customer_detail_queryset(user=request.user), pk=pk)
        if action == "archive":
            archive_customer(actor=request.user, customer=customer)
            messages.success(request, "Cliente archivado correctamente.")
        elif action == "activate":
            activate_customer(actor=request.user, customer=customer)
            messages.success(request, "Cliente activado correctamente.")
        else:
            messages.error(request, "Acción no válida.")
        fallback = reverse("customers_internal:detail", kwargs={"pk": customer.pk})
        return redirect(safe_next_url(request, request.POST.get("next"), fallback))


class InternalCustomerAddNoteView(PermissionCodeRequiredMixin, View):
    permission_code = "customers.manage"

    def post(self, request, pk):
        customer = get_object_or_404(customer_detail_queryset(user=request.user), pk=pk)
        form = CustomerNoteForm(request.POST)
        if form.is_valid():
            add_customer_note(actor=request.user, customer=customer, form=form)
            messages.success(request, "Nota agregada correctamente.")
        else:
            messages.error(request, "No se pudo guardar la nota. Revisa los datos.")
        return redirect("customers_internal:detail", pk=customer.pk)


class InternalCustomerAddInterestView(PermissionCodeRequiredMixin, View):
    permission_code = "customers.manage"

    def post(self, request, pk):
        customer = get_object_or_404(customer_detail_queryset(user=request.user), pk=pk)
        form = CustomerVehicleInterestForm(request.POST, user=request.user)
        if form.is_valid():
            add_vehicle_interest(actor=request.user, customer=customer, form=form)
            messages.success(request, "Interés vehicular agregado correctamente.")
        else:
            messages.error(request, "No se pudo guardar el interés vehicular. Revisa los datos.")
        return redirect("customers_internal:detail", pk=customer.pk)
