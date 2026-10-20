"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de inventario.

EN: This module orchestrates HTTP requests, permissions, and responses for the inventory domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the inventory domain.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from apps.accounts.views import PermissionCodeRequiredMixin
from apps.common.http import safe_next_url
from apps.inventory.forms import (
    BranchStockSettingsForm,
    InventoryCategoryForm,
    InventoryItemForm,
    InventoryItemSearchForm,
    PublicInventoryCatalogFilterForm,
    StockMovementForm,
    StockTransferForm,
)
from apps.inventory.models import InventoryItem, StockMovement
from apps.inventory.selectors import (
    active_categories_queryset,
    inventory_item_detail_queryset,
    inventory_item_queryset,
    inventory_metrics,
    low_stock_queryset,
    public_inventory_categories_queryset,
    public_inventory_item_queryset,
    stock_by_branch_queryset,
    stock_movements_queryset,
)
from apps.inventory.services import (
    activate_inventory_item,
    archive_inventory_item,
    create_inventory_category,
    create_inventory_item,
    record_stock_movement,
    transfer_stock,
    update_inventory_item,
    update_minimum_stock,
)


class PublicInventoryCatalogView(ListView):
    """ES: Catálogo público seguro. EN: Safe public inventory catalog."""

    template_name = "inventory/public/catalog.html"
    context_object_name = "items"
    paginate_by = 12

    def dispatch(self, request, *args, **kwargs):
        if not settings.VINOVA_PUBLIC_PARTS_CATALOG_ENABLED:
            raise Http404("El catálogo público de repuestos está deshabilitado.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        self.public_categories = list(public_inventory_categories_queryset())
        self.filter_form = PublicInventoryCatalogFilterForm(
            self.request.GET or None,
            categories=self.public_categories,
        )
        if self.filter_form.is_bound and not self.filter_form.is_valid():
            return InventoryItem.objects.none()
        values = self.filter_form.cleaned_data if self.filter_form.is_bound else {}
        return public_inventory_item_queryset(
            query=values.get("q", ""),
            category_slug=values.get("category", ""),
            item_type=values.get("item_type", ""),
            sort=values.get("sort", ""),
        )

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["filter_form"] = self.filter_form
        context["public_categories"] = self.public_categories
        context["has_active_filters"] = any(
            self.request.GET.get(key, "").strip() for key in ("q", "category", "item_type", "sort")
        )
        return context


class InventoryPermissionMixin(PermissionCodeRequiredMixin):
    permission_code = "inventory.view"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.has_perm_code("inventory.view") and request.user.has_perm_code("inventory.manage_stock"):
            self.permission_code = "inventory.manage_stock"
        return super().dispatch(request, *args, **kwargs)


class InternalInventoryListView(InventoryPermissionMixin, ListView):
    template_name = "inventory/internal/item_list.html"
    context_object_name = "items"
    paginate_by = 20

    def get_queryset(self):
        self.search_form = InventoryItemSearchForm(self.request.GET)
        query = status = item_type = sort = ""
        category = None
        if self.search_form.is_valid():
            query = self.search_form.cleaned_data.get("q", "")
            status = self.search_form.cleaned_data.get("status", "")
            item_type = self.search_form.cleaned_data.get("item_type", "")
            category = self.search_form.cleaned_data.get("category")
            sort = self.search_form.cleaned_data.get("sort", "")
        return inventory_item_queryset(
            user=self.request.user,
            query=query,
            status=status,
            item_type=item_type,
            category=category,
            sort=sort,
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_form"] = self.search_form
        ctx["metrics"] = inventory_metrics(self.request.user)
        ctx["recent_movements"] = stock_movements_queryset(user=self.request.user)[:8]
        return ctx


class InternalInventoryCreateView(PermissionCodeRequiredMixin, CreateView):
    permission_code = "inventory.manage_stock"
    model = InventoryItem
    form_class = InventoryItemForm
    template_name = "inventory/internal/item_form.html"

    def form_valid(self, form):
        self.object = create_inventory_item(actor=self.request.user, form=form)
        messages.success(self.request, "Artículo creado correctamente.")
        return redirect("inventory_internal:detail", pk=self.object.pk)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["mode"] = "create"
        ctx["page_heading"] = "Crear artículo"
        return ctx


class InternalInventoryDetailView(InventoryPermissionMixin, DetailView):
    template_name = "inventory/internal/item_detail.html"
    context_object_name = "item"

    def get_queryset(self):
        return inventory_item_detail_queryset(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["stock_records"] = stock_by_branch_queryset(user=self.request.user, item=self.object)
        ctx["movements"] = stock_movements_queryset(user=self.request.user, item=self.object)[:20]
        ctx["movement_form"] = StockMovementForm(
            item=self.object,
            user=self.request.user,
            initial={"item": self.object},
        )
        return ctx


class InternalInventoryUpdateView(PermissionCodeRequiredMixin, DetailView):
    permission_code = "inventory.manage_stock"
    template_name = "inventory/internal/item_form.html"
    context_object_name = "item"

    def get_queryset(self):
        return inventory_item_detail_queryset(self.request.user)

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = InventoryItemForm(instance=self.object)
        return self.render_to_response(self.get_context_data(form=form, mode="update", page_heading="Editar artículo"))

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = InventoryItemForm(request.POST, request.FILES, instance=self.object)
        if form.is_valid():
            self.object = update_inventory_item(actor=request.user, item=self.object, form=form)
            messages.success(request, "Artículo actualizado correctamente.")
            return redirect("inventory_internal:detail", pk=self.object.pk)
        return self.render_to_response(self.get_context_data(form=form, mode="update", page_heading="Editar artículo"))


class InternalInventoryStatusView(PermissionCodeRequiredMixin, View):
    permission_code = "inventory.manage_stock"

    def post(self, request, pk, action):
        item = get_object_or_404(inventory_item_detail_queryset(request.user), pk=pk)
        if action == "archive":
            archive_inventory_item(actor=request.user, item=item)
            messages.success(request, "Artículo archivado correctamente.")
        elif action == "activate":
            activate_inventory_item(actor=request.user, item=item)
            messages.success(request, "Artículo activado correctamente.")
        else:
            messages.error(request, "Acción no válida.")
        fallback = reverse("inventory_internal:detail", kwargs={"pk": item.pk})
        return redirect(safe_next_url(request, request.POST.get("next"), fallback))


class InternalStockMovementCreateView(PermissionCodeRequiredMixin, View):
    permission_code = "inventory.manage_stock"
    template_name = "inventory/internal/movement_form.html"

    def get(self, request):
        return render(
            request,
            self.template_name,
            {"form": StockMovementForm(user=request.user), "page_heading": "Registrar movimiento"},
        )

    def post(self, request):
        form = StockMovementForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                movement = record_stock_movement(
                    actor=request.user,
                    item=form.cleaned_data["item"],
                    branch=form.cleaned_data["branch"],
                    movement_type=form.cleaned_data["movement_type"],
                    quantity=form.cleaned_data["quantity"],
                    unit_cost=form.cleaned_data.get("unit_cost"),
                    reference=form.cleaned_data.get("reference", ""),
                    reason=form.cleaned_data.get("reason", ""),
                )
            except ValidationError as exc:
                form.add_error(None, exc.message if hasattr(exc, "message") else exc)
            else:
                messages.success(request, "Movimiento registrado correctamente.")
                return redirect("inventory_internal:detail", pk=movement.item.pk)
        return render(request, self.template_name, {"form": form, "page_heading": "Registrar movimiento"})


class InternalItemStockMovementCreateView(PermissionCodeRequiredMixin, View):
    permission_code = "inventory.manage_stock"

    def post(self, request, pk):
        item = get_object_or_404(inventory_item_detail_queryset(request.user), pk=pk)
        form = StockMovementForm(request.POST, item=item, user=request.user)
        if form.is_valid():
            try:
                record_stock_movement(
                    actor=request.user,
                    item=form.cleaned_data["item"],
                    branch=form.cleaned_data["branch"],
                    movement_type=form.cleaned_data["movement_type"],
                    quantity=form.cleaned_data["quantity"],
                    unit_cost=form.cleaned_data.get("unit_cost"),
                    reference=form.cleaned_data.get("reference", ""),
                    reason=form.cleaned_data.get("reason", ""),
                )
                messages.success(request, "Movimiento registrado correctamente.")
            except ValidationError as exc:
                messages.error(request, exc.message if hasattr(exc, "message") else str(exc))
        else:
            messages.error(request, "No se pudo registrar el movimiento. Revisa los datos.")
        return redirect("inventory_internal:detail", pk=item.pk)


class InternalBranchStockSettingsView(PermissionCodeRequiredMixin, View):
    """Update replenishment settings for one stock row within the actor's branch scope."""

    permission_code = "inventory.manage_stock"

    def post(self, request, pk, stock_pk):
        item = get_object_or_404(inventory_item_detail_queryset(request.user), pk=pk)
        stock = get_object_or_404(
            stock_by_branch_queryset(
                user=request.user,
                item=item,
                permission_codes=(self.permission_code,),
            ),
            pk=stock_pk,
        )
        form = BranchStockSettingsForm(request.POST, instance=stock)
        if form.is_valid():
            try:
                update_minimum_stock(
                    actor=request.user,
                    stock=stock,
                    minimum_stock=form.cleaned_data["minimum_stock"],
                    location_code=form.cleaned_data.get("location_code", ""),
                )
            except ValidationError as exc:
                messages.error(request, exc.message if hasattr(exc, "message") else str(exc))
            else:
                messages.success(request, "Reglas de reposición actualizadas correctamente.")
        else:
            messages.error(request, "No se actualizaron las reglas de reposición. Revisa los valores.")
        return redirect("inventory_internal:detail", pk=item.pk)


class InternalStockTransferCreateView(PermissionCodeRequiredMixin, View):
    permission_code = "inventory.manage_stock"
    template_name = "inventory/internal/transfer_form.html"

    def get(self, request):
        return render(
            request,
            self.template_name,
            {"form": StockTransferForm(user=request.user), "page_heading": "Transferir stock"},
        )

    def post(self, request):
        form = StockTransferForm(request.POST, user=request.user)
        if form.is_valid():
            try:
                movement = transfer_stock(
                    actor=request.user,
                    item=form.cleaned_data["item"],
                    origin_branch=form.cleaned_data["origin_branch"],
                    destination_branch=form.cleaned_data["destination_branch"],
                    quantity=form.cleaned_data["quantity"],
                    reference=form.cleaned_data.get("reference", ""),
                    reason=form.cleaned_data.get("reason", ""),
                )
            except ValidationError as exc:
                form.add_error(None, exc.message if hasattr(exc, "message") else exc)
            else:
                messages.success(request, "Transferencia registrada correctamente.")
                return redirect("inventory_internal:detail", pk=movement.item.pk)
        return render(request, self.template_name, {"form": form, "page_heading": "Transferir stock"})


class InternalStockMovementListView(InventoryPermissionMixin, ListView):
    template_name = "inventory/internal/movement_list.html"
    context_object_name = "movements"
    paginate_by = 30

    def get_queryset(self):
        query = self.request.GET.get("q", "").strip()
        movement_type = self.request.GET.get("movement_type", "").strip()
        return stock_movements_queryset(user=self.request.user, query=query, movement_type=movement_type)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["query"] = self.request.GET.get("q", "").strip()
        ctx["movement_type"] = self.request.GET.get("movement_type", "").strip()
        ctx["movement_types"] = StockMovement.MovementType.choices
        return ctx


class InternalLowStockView(InventoryPermissionMixin, ListView):
    template_name = "inventory/internal/low_stock.html"
    context_object_name = "stock_records"
    paginate_by = 30

    def get_queryset(self):
        return low_stock_queryset(self.request.user)


class InventoryCatalogDataView(PermissionCodeRequiredMixin, View):
    permission_code = "inventory.manage_stock"
    template_name = "inventory/internal/catalog_data.html"

    def get(self, request):
        return render(request, self.template_name, {"category_form": InventoryCategoryForm(), "categories": active_categories_queryset()})


class InventoryCategoryCreateView(PermissionCodeRequiredMixin, View):
    permission_code = "inventory.manage_stock"

    def post(self, request):
        form = InventoryCategoryForm(request.POST)
        if form.is_valid():
            create_inventory_category(actor=request.user, form=form)
            messages.success(request, "Categoría creada correctamente.")
        else:
            messages.error(request, "No se pudo crear la categoría. Revisa los datos.")
        return redirect("inventory_internal:catalog_data")
