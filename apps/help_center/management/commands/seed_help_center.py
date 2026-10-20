"""ES: Implementa el comando administrativo «seed help center» para ayuda.

EN: Implements the «seed help center» management command for help center.

Contexto existente / Existing context:
Django management command for seed help center.
"""

from __future__ import annotations

from django.core.management.base import BaseCommand
from django.db import transaction

from apps.help_center.content import ARTICLES, CATEGORIES, CHECKLISTS
from apps.help_center.models import HelpArticle, HelpCategory, HelpChecklist, HelpChecklistItem


class Command(BaseCommand):
    help = "Carga o actualiza el contenido base del Centro de ayuda de Vinova Pro."

    @transaction.atomic
    def handle(self, *args, **options):
        categories = {}
        for definition in CATEGORIES:
            values = definition.copy()
            slug = values.pop("slug")
            category, _ = HelpCategory.objects.update_or_create(slug=slug, defaults=values)
            categories[slug] = category

        for definition in ARTICLES:
            values = definition.copy()
            slug = values.pop("slug")
            category_slug = values.pop("category")
            HelpArticle.objects.update_or_create(
                slug=slug,
                defaults={"category": categories[category_slug], **values},
            )

        for definition in CHECKLISTS:
            values = definition.copy()
            items = values.pop("items")
            slug = values.pop("slug")
            checklist, _ = HelpChecklist.objects.update_or_create(slug=slug, defaults=values)
            expected_orders = []
            for order, (title, instructions, route_name) in enumerate(items, start=10):
                expected_orders.append(order)
                HelpChecklistItem.objects.update_or_create(
                    checklist=checklist,
                    order=order,
                    defaults={
                        "title": title,
                        "instructions": instructions,
                        "route_name": route_name,
                        "is_required": True,
                    },
                )
            checklist.items.exclude(order__in=expected_orders).delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Centro de ayuda actualizado: {len(CATEGORIES)} categorías, "
                f"{len(ARTICLES)} artículos y {len(CHECKLISTS)} checklists."
            )
        )
