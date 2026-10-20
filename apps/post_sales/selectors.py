"""ES: Este módulo implementa consultas de lectura conscientes de autorización para el dominio de postventa.

EN: This module implements authorization-aware read queries for the post sales domain.

Contexto existente / Existing context:
Read queries and authorization-aware selectors for the post sales domain.
"""

from django.db.models import Count, Q, Sum

from apps.accounts.scopes import scope_queryset_to_user_branches
from apps.post_sales.models import ServiceOrder


POST_SALES_PERMISSIONS = ("post_sales.view", "post_sales.manage")


def service_orders_queryset(user, *, status="", query=""):
    qs = ServiceOrder.objects.select_related("branch", "customer", "vehicle", "vehicle__brand", "vehicle__model", "responsible")
    qs = scope_queryset_to_user_branches(
        qs,
        user=user,
        permission_codes=POST_SALES_PERMISSIONS,
    )
    if status:
        qs = qs.filter(status=status)
    if query:
        qs = qs.filter(number__icontains=query)
    return qs


def service_order_detail_queryset(user):
    return service_orders_queryset(user).prefetch_related("lines", "documents", "history__changed_by")


def service_order_metrics(user):
    qs = service_orders_queryset(user)
    return qs.aggregate(
        total=Count("id"),
        open=Count("id", filter=Q(status__in=(ServiceOrder.Status.SCHEDULED, ServiceOrder.Status.IN_PROGRESS))),
        completed=Count("id", filter=Q(status=ServiceOrder.Status.COMPLETED)),
        total_cost=Sum("total_cost"),
    )
