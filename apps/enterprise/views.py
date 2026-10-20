"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de configuración empresarial.

EN: This module orchestrates HTTP requests, permissions, and responses for the enterprise domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the enterprise domain.
"""

from __future__ import annotations

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import TemplateView, UpdateView

from apps.accounts.scopes import has_global_permission
from apps.accounts.views import PermissionCodeRequiredMixin
from apps.enterprise.forms import ApprovalPolicyForm, CompanyCoreForm, LegalSettingsForm, PublicContactForm, PublicSiteForm
from apps.enterprise.models import ApprovalPolicy
from apps.enterprise.selectors import approval_policy_queryset, get_enterprise_overview, get_primary_company, get_public_settings
from apps.enterprise.services import ensure_default_approval_policies, update_approval_policy, update_company_core, update_public_settings
from apps.sri_integration.selectors import get_or_create_sri_configuration


class EnterpriseManageMixin(PermissionCodeRequiredMixin):
    permission_code = "enterprise.manage"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if not has_global_permission(request.user, self.permission_code):
            raise PermissionDenied("Solo el rango más alto puede administrar el centro empresarial.")
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


class EnterpriseHomeView(EnterpriseManageMixin, TemplateView):
    template_name = "enterprise/internal/home.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx.update(get_enterprise_overview())
        ctx["approval_policies"] = approval_policy_queryset(self.company)
        return ctx


class CompanyProfileUpdateView(EnterpriseManageMixin, UpdateView):
    form_class = CompanyCoreForm
    template_name = "enterprise/internal/company_form.html"

    def get_object(self):
        return self.company

    def form_valid(self, form):
        self.object = update_company_core(actor=self.request.user, company=self.company, form=form)
        messages.success(self.request, "Datos de empresa actualizados correctamente.")
        return redirect("enterprise:profile")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["section_title"] = "Perfil empresarial"
        ctx["section_description"] = "Datos centrales de la empresa dueña de esta instalación. No es multi-tenant."
        return ctx


class PublicSiteUpdateView(EnterpriseManageMixin, UpdateView):
    form_class = PublicSiteForm
    template_name = "enterprise/internal/settings_form.html"

    def get_object(self):
        return self.public_settings

    def form_valid(self, form):
        self.object = update_public_settings(actor=self.request.user, settings=self.public_settings, form=form, action="enterprise.public_site.update")
        messages.success(self.request, "Portada pública actualizada correctamente.")
        return redirect("enterprise:public_site")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["section_title"] = "Portada pública y catálogo"
        ctx["section_description"] = "Textos comerciales visibles en la web pública sin editar HTML ni archivos del proyecto."
        return ctx


class PublicContactUpdateView(EnterpriseManageMixin, UpdateView):
    form_class = PublicContactForm
    template_name = "enterprise/internal/settings_form.html"

    def get_object(self):
        return self.public_settings

    def form_valid(self, form):
        self.object = update_public_settings(actor=self.request.user, settings=self.public_settings, form=form, action="enterprise.contact.update")
        messages.success(self.request, "Contacto público actualizado correctamente.")
        return redirect("enterprise:contact")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["section_title"] = "Contacto, horarios y redes"
        ctx["section_description"] = "Información pública que aparece en portada, footer y llamadas de atención."
        return ctx


class LegalSettingsUpdateView(EnterpriseManageMixin, UpdateView):
    form_class = LegalSettingsForm
    template_name = "enterprise/internal/settings_form.html"

    def get_object(self):
        return self.public_settings

    def form_valid(self, form):
        self.object = update_public_settings(actor=self.request.user, settings=self.public_settings, form=form, action="enterprise.legal.update")
        messages.success(self.request, "Textos legales actualizados correctamente.")
        return redirect("enterprise:legal")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["section_title"] = "Legal y protección de datos"
        ctx["section_description"] = "Base editable para privacidad, términos y tratamiento de datos personales."
        return ctx


class ApprovalPolicyListView(EnterpriseManageMixin, TemplateView):
    template_name = "enterprise/internal/approval_policy_list.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["approval_policies"] = approval_policy_queryset(self.company)
        return ctx


class ApprovalPolicyUpdateView(EnterpriseManageMixin, UpdateView):
    form_class = ApprovalPolicyForm
    template_name = "enterprise/internal/approval_policy_form.html"
    context_object_name = "policy"

    def get_object(self):
        return get_object_or_404(ApprovalPolicy, company=self.company, pk=self.kwargs["pk"])

    def form_valid(self, form):
        self.object = update_approval_policy(actor=self.request.user, policy=self.object, form=form)
        messages.success(self.request, "Política de aprobación actualizada correctamente.")
        return redirect("enterprise:approval_policies")
