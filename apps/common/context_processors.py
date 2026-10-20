"""ES: Este módulo implementa el componente context processors para el dominio de infraestructura compartida.

EN: This module implements the context processors component for the common domain.

Contexto existente / Existing context:
Template context providers for the common domain.
"""

from django.conf import settings
from django.db.models import Q

from apps.common.modules import is_module_enabled


def optional_modules_context(request):
    user = getattr(request, "user", None)
    can_view_post_sales = bool(
        is_module_enabled("post_sales")
        and user
        and user.is_authenticated
        and (user.has_perm_code("post_sales.view") or user.has_perm_code("post_sales.manage"))
    )
    return {
        "vinova_product_version": settings.VINOVA_PRODUCT_VERSION,
        "optional_modules": {
            "post_sales": can_view_post_sales,
        },
        "portal_modules": {
            "post_sales": bool(
                is_module_enabled("post_sales")
                and user
                and user.is_authenticated
                and user.has_perm_code("portal.access")
            ),
        },
        "public_modules": {
            "parts_catalog": bool(settings.VINOVA_PUBLIC_PARTS_CATALOG_ENABLED),
        },
    }


def staff_shell_context(request):
    """Datos del shell interno: sucursal asignada y notificaciones sin leer.

    El conteo respeta los permisos del usuario y solo consulta cuando el módulo
    de notificaciones está habilitado; nunca expone datos de otras sucursales.
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {
            "staff_unread_notifications": 0,
            "portal_unread_notifications": 0,
            "staff_branch_label": None,
        }

    branch = getattr(user, "branch", None)
    unread = 0
    if user.has_perm_code("notifications.view"):
        from apps.notifications.models import NotificationRecipient

        unread = NotificationRecipient.objects.filter(
            user=user,
            status=NotificationRecipient.DeliveryStatus.UNREAD,
        ).count()

    portal_unread = getattr(request, "portal_unread_notifications", 0)
    portal_customer = getattr(request, "portal_customer", None)
    if portal_customer is not None and not hasattr(request, "portal_unread_notifications"):
        annotated_count = getattr(portal_customer, "portal_unread_count", None)
        if annotated_count is not None:
            portal_unread = annotated_count
        else:
            from apps.notifications.models import NotificationRecipient

            owned = Q(
                recipient_type=NotificationRecipient.RecipientType.CUSTOMER,
                customer=portal_customer,
            )
            if portal_customer.account_id:
                owned |= Q(
                    recipient_type=NotificationRecipient.RecipientType.USER,
                    user_id=portal_customer.account_id,
                )
            portal_unread = NotificationRecipient.objects.filter(
                owned,
                status=NotificationRecipient.DeliveryStatus.UNREAD,
                notification__is_deleted=False,
                notification__status="sent",
            ).count()

    return {
        "staff_unread_notifications": unread,
        "portal_unread_notifications": portal_unread,
        "staff_branch_label": getattr(branch, "name", None) if branch else None,
    }
