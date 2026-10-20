"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de empresa.

EN: This module orchestrates HTTP requests, permissions, and responses for the companies domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the companies domain.
"""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.views.generic import CreateView, DetailView, ListView, UpdateView

from apps.accounts.scopes import has_global_permission
from apps.accounts.views import PermissionCodeRequiredMixin
from apps.companies.forms import CompanyForm, CompanySearchForm
from apps.companies.models import Company
from apps.companies.selectors import company_detail_queryset, company_list_queryset
from apps.companies.services import create_company, update_company


class GlobalCompanyAccessMixin(PermissionCodeRequiredMixin):
    permission_code = "companies.manage"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not has_global_permission(request.user, self.permission_code):
            raise PermissionDenied("La configuración de empresa requiere un permiso global.")
        return super().dispatch(request, *args, **kwargs)


class CompanyListView(GlobalCompanyAccessMixin, ListView):
    template_name = "companies/company_list.html"
    context_object_name = "companies"
    paginate_by = 20

    def get_queryset(self):
        self.search_form = CompanySearchForm(self.request.GET)
        query = ""
        if self.search_form.is_valid():
            query = self.search_form.cleaned_data.get("q", "")
        return company_list_queryset(query=query)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_form"] = self.search_form
        ctx["query"] = self.request.GET.get("q", "")
        return ctx


class CompanyCreateView(GlobalCompanyAccessMixin, CreateView):
    template_name = "companies/company_form.html"
    form_class = CompanyForm
    model = Company

    def form_valid(self, form):
        self.object = create_company(actor=self.request.user, form=form)
        messages.success(self.request, "Empresa creada correctamente.")
        return redirect("companies:detail", pk=self.object.pk)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["mode"] = "create"
        ctx["page_heading"] = "Crear empresa"
        return ctx


class CompanyDetailView(GlobalCompanyAccessMixin, DetailView):
    template_name = "companies/company_detail.html"
    context_object_name = "company"

    def get_queryset(self):
        return company_detail_queryset()


class CompanyUpdateView(GlobalCompanyAccessMixin, UpdateView):
    template_name = "companies/company_form.html"
    form_class = CompanyForm
    context_object_name = "company"

    def get_queryset(self):
        return company_detail_queryset()

    def form_valid(self, form):
        self.object = update_company(actor=self.request.user, company=self.object, form=form)
        messages.success(self.request, "Empresa actualizada correctamente.")
        return redirect("companies:detail", pk=self.object.pk)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["mode"] = "update"
        ctx["page_heading"] = "Editar empresa"
        return ctx
