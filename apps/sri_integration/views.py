"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de configuración SRI heredada.

EN: This module orchestrates HTTP requests, permissions, and responses for the sri integration domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the sri integration domain.
"""

from __future__ import annotations

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import CreateView, TemplateView, UpdateView

from apps.accounts.scopes import has_global_permission
from apps.accounts.views import PermissionCodeRequiredMixin
from apps.enterprise.selectors import get_primary_company, get_public_settings
from apps.enterprise.services import ensure_default_approval_policies
from apps.sri_integration.forms import SriConfigurationForm, SriEstablishmentForm, SriSequenceForm
from apps.sri_integration.models import SriEstablishment, SriSequence
from apps.sri_integration.selectors import get_or_create_sri_configuration, sri_establishment_queryset, sri_sequence_queryset
from apps.sri_integration.services import create_or_update_establishment, create_or_update_sequence, update_sri_configuration


class SriManageMixin(PermissionCodeRequiredMixin):
    permission_code = "sri.manage"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not has_global_permission(request.user, self.permission_code):
            raise PermissionDenied("Solo el rango más alto puede administrar configuración SRI.")
        self.company = get_primary_company()
        if not self.company:
            messages.warning(request, "Primero debes crear la empresa principal de esta instalación.")
            return redirect("companies:create")
        self.public_settings = get_public_settings(self.company)
        self.sri_configuration = get_or_create_sri_configuration(self.company)
        ensure_default_approval_policies(company=self.company)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["company"] = self.company
        ctx["public_settings"] = self.public_settings
        ctx["sri_configuration"] = self.sri_configuration
        ctx["enterprise_nav"] = [
            ("Resumen", reverse("enterprise:home")),
            ("Empresa", reverse("enterprise:profile")),
            ("Portada pública", reverse("enterprise:public_site")),
            ("Contacto", reverse("enterprise:contact")),
            ("Legal y datos", reverse("enterprise:legal")),
            ("SRI base", reverse("sri_integration:configuration")),
            ("Establecimientos SRI", reverse("sri_integration:establishments")),
            ("Secuenciales", reverse("sri_integration:sequences")),
            ("Aprobaciones", reverse("enterprise:approval_policies")),
        ]
        return ctx


class SriConfigurationUpdateView(SriManageMixin, UpdateView):
    form_class = SriConfigurationForm
    template_name = "sri_integration/internal/configuration_form.html"

    def get_object(self):
        return self.sri_configuration

    def form_valid(self, form):
        self.object = update_sri_configuration(actor=self.request.user, config=self.sri_configuration, form=form)
        messages.success(self.request, "Configuración SRI base actualizada correctamente.")
        return redirect("sri_integration:configuration")


class SriEstablishmentListView(SriManageMixin, TemplateView):
    template_name = "sri_integration/internal/establishment_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["establishments"] = sri_establishment_queryset(self.sri_configuration)
        return ctx


class SriEstablishmentCreateView(SriManageMixin, CreateView):
    form_class = SriEstablishmentForm
    template_name = "sri_integration/internal/establishment_form.html"

    def form_valid(self, form):
        self.object = create_or_update_establishment(actor=self.request.user, configuration=self.sri_configuration, form=form)
        messages.success(self.request, "Establecimiento SRI creado correctamente.")
        return redirect("sri_integration:establishments")


class SriEstablishmentUpdateView(SriManageMixin, UpdateView):
    form_class = SriEstablishmentForm
    template_name = "sri_integration/internal/establishment_form.html"
    context_object_name = "establishment"

    def get_object(self):
        return get_object_or_404(SriEstablishment, configuration=self.sri_configuration, pk=self.kwargs["pk"])

    def form_valid(self, form):
        self.object = create_or_update_establishment(actor=self.request.user, configuration=self.sri_configuration, form=form)
        messages.success(self.request, "Establecimiento SRI actualizado correctamente.")
        return redirect("sri_integration:establishments")


class SriSequenceListView(SriManageMixin, TemplateView):
    template_name = "sri_integration/internal/sequence_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["sequences"] = sri_sequence_queryset(self.sri_configuration)
        return ctx


class SriSequenceCreateView(SriManageMixin, CreateView):
    form_class = SriSequenceForm
    template_name = "sri_integration/internal/sequence_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["configuration"] = self.sri_configuration
        return kwargs

    def form_valid(self, form):
        self.object = create_or_update_sequence(actor=self.request.user, form=form)
        messages.success(self.request, "Secuencia SRI creada correctamente.")
        return redirect("sri_integration:sequences")


class SriSequenceUpdateView(SriManageMixin, UpdateView):
    form_class = SriSequenceForm
    template_name = "sri_integration/internal/sequence_form.html"
    context_object_name = "sequence"

    def get_object(self):
        return get_object_or_404(SriSequence, establishment__configuration=self.sri_configuration, pk=self.kwargs["pk"])

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["configuration"] = self.sri_configuration
        return kwargs

    def form_valid(self, form):
        self.object = create_or_update_sequence(actor=self.request.user, form=form)
        messages.success(self.request, "Secuencia SRI actualizada correctamente.")
        return redirect("sri_integration:sequences")
