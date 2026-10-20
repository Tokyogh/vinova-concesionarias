"""ES: Este módulo implementa el componente lookups para el dominio de infraestructura compartida.

EN: This module implements the lookups component for the common domain.

Contexto existente / Existing context:
Lookups support for the common domain.
"""

from __future__ import annotations

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Q
from django.http import JsonResponse
from django.views import View

from apps.accounts.scopes import accessible_branches_queryset, accessible_users_queryset, scope_queryset_to_user_branches
from apps.customers.models import Customer
from apps.documents.models import PrivateDocument, ReusableAsset
from apps.inventory.models import InventoryItem
from apps.sales.models import SaleRecord
from apps.vehicles.models import Vehicle


class InternalLookupView(LoginRequiredMixin, View):
    """JSON endpoints for searchable selects in internal forms.

    They keep the interface usable when there are hundreds or thousands of
    records and avoid telling non-technical staff to paste IDs or file paths.
    """

    max_results = 20

    def get(self, request, resource):
        q = (request.GET.get("q") or "").strip()
        if len(q) > 120:
            q = q[:120]
        handlers = {
            "users": self.users,
            "branches": self.branches,
            "customers": self.customers,
            "vehicles": self.vehicles,
            "inventory-items": self.inventory_items,
            "sales": self.sales,
            "documents": self.documents,
            "assets": self.assets,
        }
        handler = handlers.get(resource)
        if not handler:
            return JsonResponse({"results": []}, status=404)
        return JsonResponse({"results": handler(request, q)})

    def users(self, request, q):
        if not request.user.has_perm_code("accounts.manage_users") and not request.user.has_perm_code("notifications.send"):
            return []
        permission_codes = ("accounts.manage_users",) if request.user.has_perm_code("accounts.manage_users") else ("notifications.send",)
        qs = accessible_users_queryset(request.user, permission_codes=permission_codes)
        if q:
            qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(username__icontains=q) | Q(email__icontains=q))
        return [{"id": obj.id, "text": f"{obj.get_full_name() or obj.username} · {obj.email}"} for obj in qs.order_by("first_name", "last_name", "username")[: self.max_results]]

    def branches(self, request, q):
        if not request.user.can_access_internal_panel:
            return []
        permission_codes = ("notifications.send",) if request.user.has_perm_code("notifications.send") else ("dashboard.view",)
        qs = accessible_branches_queryset(request.user, permission_codes=permission_codes)
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(city__icontains=q) | Q(company__commercial_name__icontains=q))
        return [{"id": obj.id, "text": f"{obj.company.commercial_name} · {obj.name} · {obj.city}"} for obj in qs.order_by("company__commercial_name", "name")[: self.max_results]]

    def customers(self, request, q):
        if not request.user.can_view_customers and not request.user.has_perm_code("notifications.send"):
            return []
        permission_codes = ("customers.view",) if request.user.can_view_customers else ("notifications.send",)
        qs = scope_queryset_to_user_branches(Customer.objects.filter(is_deleted=False), user=request.user, permission_codes=permission_codes, branch_lookup="assigned_branch")
        if q:
            qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(business_name__icontains=q) | Q(identification_number__icontains=q) | Q(email__icontains=q) | Q(phone__icontains=q))
        return [{"id": obj.id, "text": f"{obj.display_name} · {obj.identification_number or obj.email or obj.phone or 'sin identificación'}"} for obj in qs.order_by("business_name", "first_name", "last_name")[: self.max_results]]

    def vehicles(self, request, q):
        if not request.user.can_view_internal_vehicles and not request.user.has_perm_code("notifications.send"):
            return []
        permission_codes = ("vehicles.view",) if request.user.can_view_internal_vehicles else ("notifications.send",)
        qs = scope_queryset_to_user_branches(Vehicle.objects.filter(is_deleted=False).select_related("brand", "model", "branch"), user=request.user, permission_codes=permission_codes)
        if q:
            qs = qs.filter(Q(brand__name__icontains=q) | Q(model__name__icontains=q) | Q(internal_code__icontains=q) | Q(vin__icontains=q) | Q(plate__icontains=q) | Q(color__icontains=q))
        return [{"id": obj.id, "text": f"{obj.brand.name} {obj.model.name} {obj.year} · {obj.internal_code} · {obj.plate or obj.vin or 'sin placa/VIN'}"} for obj in qs.order_by("brand__name", "model__name", "-year")[: self.max_results]]

    def inventory_items(self, request, q):
        if not request.user.can_view_inventory and not request.user.can_access_sales:
            return []
        qs = InventoryItem.objects.filter(is_deleted=False)
        if q:
            qs = qs.filter(Q(name__icontains=q) | Q(sku__icontains=q) | Q(description__icontains=q))
        return [{"id": obj.id, "text": f"{obj.sku} · {obj.name}"} for obj in qs.order_by("sku", "name")[: self.max_results]]

    def sales(self, request, q):
        if not request.user.can_access_sales and not request.user.has_perm_code("notifications.send"):
            return []
        permission_codes = ("sales.quote", "sales.reserve", "sales.sell") if request.user.can_access_sales else ("notifications.send",)
        qs = scope_queryset_to_user_branches(SaleRecord.objects.filter(is_deleted=False).select_related("customer"), user=request.user, permission_codes=permission_codes)
        if q:
            qs = qs.filter(Q(number__icontains=q) | Q(customer__first_name__icontains=q) | Q(customer__last_name__icontains=q) | Q(customer__business_name__icontains=q) | Q(customer__identification_number__icontains=q))
        return [{"id": obj.id, "text": f"{obj.number} · {obj.customer.display_name} · {obj.get_status_display()}"} for obj in qs.order_by("-created_at")[: self.max_results]]

    def documents(self, request, q):
        if not request.user.can_view_documents:
            return []
        qs = scope_queryset_to_user_branches(PrivateDocument.objects.filter(is_deleted=False).select_related("customer", "vehicle", "sale"), user=request.user, permission_codes=("documents.view",))
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(original_name__icontains=q) | Q(customer__business_name__icontains=q) | Q(customer__first_name__icontains=q) | Q(customer__last_name__icontains=q) | Q(vehicle__internal_code__icontains=q) | Q(vehicle__vin__icontains=q) | Q(vehicle__plate__icontains=q) | Q(sale__number__icontains=q))
        return [{"id": obj.id, "text": f"{obj.title} · {obj.get_document_type_display()}"} for obj in qs.order_by("-created_at")[: self.max_results]]

    def assets(self, request, q):
        if not request.user.can_view_documents and not request.user.can_manage_vehicles:
            return []
        qs = ReusableAsset.objects.filter(is_deleted=False, is_active=True)
        if q:
            qs = qs.filter(Q(title__icontains=q) | Q(original_name__icontains=q) | Q(description__icontains=q))
        return [{"id": obj.id, "text": f"{obj.title} · {obj.get_asset_type_display()}"} for obj in qs.order_by("-created_at")[: self.max_results]]
