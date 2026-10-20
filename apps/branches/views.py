"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de sucursales.

EN: This module orchestrates HTTP requests, permissions, and responses for the branches domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the branches domain.
"""

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect
from django.conf import settings
from django.views.generic import CreateView, DetailView, ListView, TemplateView, UpdateView

from apps.accounts.scopes import has_global_permission
from apps.accounts.views import PermissionCodeRequiredMixin
from apps.branches.forms import BranchForm, BranchSearchForm
from apps.branches.models import Branch
from apps.branches.selectors import branch_detail_queryset, branch_list_queryset, public_institution_queryset
from apps.branches.services import create_branch, update_branch


class GlobalBranchAccessMixin(PermissionCodeRequiredMixin):
    permission_code = "branches.manage"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not has_global_permission(request.user, self.permission_code):
            raise PermissionDenied("La configuración de sucursales requiere un permiso global.")
        return super().dispatch(request, *args, **kwargs)


class PublicInstitutionListView(TemplateView):
    template_name = "branches/public_institutions.html"
    valid_types = {"institution", "dealership", "service_center"}

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        institutions = list(public_institution_queryset())
        active_type = self.request.GET.get("tipo", "").strip()
        if active_type not in self.valid_types:
            active_type = ""
        counts = {type_code: 0 for type_code in self.valid_types}
        for institution in institutions:
            category = institution.public_category
            if category in counts:
                counts[category] += 1
        context.update(
            institutions=institutions,
            institution_counts=counts,
            active_type=active_type,
            maptiler_public_key=settings.MAPTILER_PUBLIC_KEY,
        )
        return context


class BranchListView(GlobalBranchAccessMixin, ListView):
    template_name = "branches/branch_list.html"
    context_object_name = "branches"
    paginate_by = 20

    def get_queryset(self):
        self.search_form = BranchSearchForm(self.request.GET)
        query = ""
        branch_type = ""
        if self.search_form.is_valid():
            query = self.search_form.cleaned_data.get("q", "")
            branch_type = self.search_form.cleaned_data.get("branch_type", "")
        return branch_list_queryset(query=query, branch_type=branch_type)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_form"] = self.search_form
        ctx["query"] = self.request.GET.get("q", "")
        ctx["branch_type"] = self.request.GET.get("branch_type", "")
        return ctx


class BranchCreateView(GlobalBranchAccessMixin, CreateView):
    template_name = "branches/branch_form.html"
    form_class = BranchForm
    model = Branch

    def form_valid(self, form):
        self.object = create_branch(actor=self.request.user, form=form)
        messages.success(self.request, "Sucursal creada correctamente.")
        return redirect("branches:detail", pk=self.object.pk)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["mode"] = "create"
        ctx["page_heading"] = "Crear sucursal"
        return ctx


class BranchDetailView(GlobalBranchAccessMixin, DetailView):
    template_name = "branches/branch_detail.html"
    context_object_name = "branch"

    def get_queryset(self):
        return branch_detail_queryset()


class BranchUpdateView(GlobalBranchAccessMixin, UpdateView):
    template_name = "branches/branch_form.html"
    form_class = BranchForm
    context_object_name = "branch"

    def get_queryset(self):
        return branch_detail_queryset()

    def form_valid(self, form):
        self.object = update_branch(actor=self.request.user, branch=self.object, form=form)
        messages.success(self.request, "Sucursal actualizada correctamente.")
        return redirect("branches:detail", pk=self.object.pk)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["mode"] = "update"
        ctx["page_heading"] = "Editar sucursal"
        return ctx
