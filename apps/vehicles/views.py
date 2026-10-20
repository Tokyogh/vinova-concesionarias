"""ES: Este módulo orquesta solicitudes HTTP, permisos y respuestas para el dominio de vehículos.

EN: This module orchestrates HTTP requests, permissions, and responses for the vehicles domain.

Contexto existente / Existing context:
HTTP views and request orchestration for the vehicles domain.
"""

from __future__ import annotations

from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, DetailView, ListView

from apps.accounts.scopes import accessible_branch_ids
from apps.accounts.views import PermissionCodeRequiredMixin
from apps.analytics.models import VehicleInteraction
from apps.analytics.services import record_vehicle_interaction
from apps.common.http import safe_next_url
from apps.customers.models import Customer
from apps.customers.selectors import linkable_customer_queryset
from apps.vehicles.forms import (
    VehicleBrandForm,
    VehicleCommercialHighlightForm,
    VehicleForm,
    VehicleMediaMetadataForm,
    VehicleMediaUploadForm,
    VehicleModelForm,
    VehiclePartSpecificationForm,
    VehicleSearchForm,
)
from apps.vehicles.models import Vehicle, VehicleMedia, VehiclePartSpecification
from apps.vehicles.selectors import (
    accessible_vehicle_queryset,
    brand_list_queryset,
    internal_vehicle_queryset,
    model_list_queryset,
    public_vehicle_queryset,
    vehicle_detail_queryset,
    vehicle_link_codes_queryset,
    vehicle_links_queryset,
)
from apps.vehicles.services import (
    archive_vehicle,
    create_brand,
    create_model,
    create_vehicle,
    generate_vehicle_link_code,
    hide_vehicle,
    publish_vehicle,
    redeem_link_code,
    remove_vehicle_highlight,
    remove_vehicle_media,
    remove_vehicle_part_specification,
    revoke_vehicle_link_code,
    save_vehicle_highlight,
    save_vehicle_part_specification,
    transfer_customer_vehicle,
    unlink_customer_vehicle,
    update_vehicle,
    update_vehicle_media,
    upload_vehicle_media,
)


class VehicleCatalogView(View):
    """Catálogo público de vehículos.

    No requiere login y no muestra información de staff. La administración de
    vehículos vive en /dashboard/vehicles/.
    """

    template_name = "vehicles/catalog.html"

    ORDERING_CHOICES = {
        "destacados": ["-is_featured", "-created_at"],
        "precio-asc": ["price", "-created_at"],
        "precio-desc": ["-price", "-created_at"],
        "anio-desc": ["-year", "-created_at"],
        "anio-asc": ["year", "-created_at"],
        "kilometraje": ["mileage", "-created_at"],
    }

    def get(self, request):
        """ES: Procesa solicitudes GET de VehicleCatalogView aplicando el flujo del dominio de vehículos.

        EN: Processes GET requests on VehicleCatalogView using the vehicles domain flow.
        """

        base = public_vehicle_queryset()
        params = request.GET

        query = params.get("q", "").strip()
        brand = params.get("marca", "").strip()
        model = params.get("modelo", "").strip()
        segment = params.get("tipo", "").strip()
        price_min = self._decimal(params.get("precio_min"))
        price_max = self._decimal(params.get("precio_max"))
        year_min = self._int(params.get("anio_min"))
        year_max = self._int(params.get("anio_max"))
        ordering = params.get("orden", "")
        if ordering not in self.ORDERING_CHOICES:
            ordering = ""

        qs = base
        if query:
            qs = qs.filter(
                Q(model__name__icontains=query)
                | Q(brand__name__icontains=query)
                | Q(model__segment__icontains=query)
                | Q(version__icontains=query)
                | Q(color__icontains=query)
                | Q(branch__city__icontains=query)
            )
        if brand:
            qs = qs.filter(brand_id=brand)
        if model:
            qs = qs.filter(model_id=model)
        if segment:
            qs = qs.filter(model__segment__iexact=segment)
        if price_min is not None:
            qs = qs.filter(price__gte=price_min)
        if price_max is not None:
            qs = qs.filter(price__lte=price_max)
        if year_min:
            qs = qs.filter(year__gte=year_min)
        if year_max:
            qs = qs.filter(year__lte=year_max)

        qs = qs.order_by(*self.ORDERING_CHOICES[ordering or "destacados"])

        total = qs.count()
        page = Paginator(qs, 12).get_page(params.get("page"))

        years = base.order_by().values_list("year", flat=True).distinct()
        context = {
            "page": page,
            "query": query,
            "total_results": total,
            "brands": base.values("brand_id", "brand__name").annotate(total=Count("id")).order_by("brand__name"),
            "models": base.values("model_id", "model__name", "brand_id").annotate(total=Count("id")).order_by("model__name"),
            "segments": base.exclude(model__segment="").values("model__segment").annotate(total=Count("id")).order_by("model__segment"),
            "year_bounds": (years.order_by("year").first(), years.order_by("-year").first()),
            "selected": {
                "marca": brand,
                "modelo": model,
                "tipo": segment,
                "precio_min": params.get("precio_min", "").strip(),
                "precio_max": params.get("precio_max", "").strip(),
                "anio_min": params.get("anio_min", "").strip(),
                "anio_max": params.get("anio_max", "").strip(),
            },
            "ordering": ordering,
            "ordering_choices": (
                ("destacados", "Destacados"),
                ("precio-asc", "Menor precio"),
                ("precio-desc", "Mayor precio"),
                ("anio-desc", "Más reciente"),
                ("anio-asc", "Más antiguo"),
                ("kilometraje", "Menor kilometraje"),
            ),
        }
        return render(request, self.template_name, context)

    @staticmethod
    def _decimal(value):
        try:
            return Decimal(str(value).replace(",", ".").strip())
        except (InvalidOperation, TypeError, ValueError):
            return None

    @staticmethod
    def _int(value):
        try:
            return int(str(value).strip())
        except (TypeError, ValueError):
            return None


class VehicleDetailModalView(View):
    template_name = "vehicles/partials/vehicle_detail_modal.html"

    def get(self, request, pk):
        vehicle = get_object_or_404(public_vehicle_queryset(), pk=pk)
        record_vehicle_interaction(request=request, event_type=VehicleInteraction.EventType.DETAIL_VIEW, vehicle=vehicle)
        return render(request, self.template_name, {"vehicle": vehicle})


class VehiclePublicDetailView(View):
    """Ficha pública de vehículo.

    Usa el mismo queryset público que el catálogo y la ficha modal, de modo que
    nunca expone vehículos sin publicar. El contenido se deriva de datos
    existentes (medios, especificaciones por parte, sucursal y precio).
    """

    template_name = "vehicles/detail.html"

    HEADLINE_SPEC_LABELS = {
        "transmision": ("Transmisión", "Transmisión"),
        "transmission": ("Transmisión", "Transmisión"),
        "combustible": ("Combustible", "Combustible"),
        "fuel": ("Combustible", "Combustible"),
        "pasajeros": ("Pasajeros", "Pasajeros"),
        "passengers": ("Pasajeros", "Pasajeros"),
        "ocupantes": ("Pasajeros", "Pasajeros"),
        "motor": ("Motor", "Motor"),
        "cilindrada": ("Cilindrada", "Cilindrada"),
        "potencia": ("Potencia", "Potencia"),
        "traccion": ("Tracción", "Tracción"),
        "longitud": ("Largo", "Dimensiones"),
        "ancho": ("Ancho", "Dimensiones"),
        "altura": ("Alto", "Dimensiones"),
        "distancia": ("Distancia entre ejes", "Dimensiones"),
    }

    FEATURE_CODES = ("engine", "transmission", "suspension")
    EQUIPMENT_CODES = ("technology", "interior", "safety", "exterior")
    DIMENSION_CODES = ("cargo", "other")

    def get(self, request, slug):
        vehicle = get_object_or_404(
            public_vehicle_queryset().prefetch_related("media__resource", "part_specs__image"),
            public_slug=slug,
        )
        record_vehicle_interaction(request=request, event_type=VehicleInteraction.EventType.DETAIL_VIEW, vehicle=vehicle)

        gallery = [
            media
            for media in vehicle.media.all()
            if media.is_public and media.media_type in {VehicleMedia.MediaType.HERO, VehicleMedia.MediaType.IMAGE} and media.resource.file
        ]
        gallery.sort(key=lambda media: media.order)

        specs = list(vehicle.part_specs.all())
        by_code: dict[str, list[VehiclePartSpecification]] = {}
        for part in specs:
            by_code.setdefault(part.part_code, []).append(part)

        related = (
            public_vehicle_queryset()
            .filter(model__segment=vehicle.model.segment)
            .exclude(pk=vehicle.pk)
            .order_by("-is_featured", "-created_at")[:3]
        )

        context = {
            "vehicle": vehicle,
            "gallery": gallery,
            "model_3d": vehicle.active_model_3d,
            "headline_specs": self._headline_specs(vehicle, specs),
            "feature_parts": self._flatten(by_code, self.FEATURE_CODES),
            "equipment_parts": self._flatten(by_code, self.EQUIPMENT_CODES),
            "dimension_parts": self._flatten(by_code, self.DIMENSION_CODES),
            "related_vehicles": related,
            "tab_groups": [
                ("features", "Características", self._flatten(by_code, self.FEATURE_CODES)),
                ("equipment", "Equipamiento", self._flatten(by_code, self.EQUIPMENT_CODES)),
                ("dimensions", "Dimensiones", self._flatten(by_code, self.DIMENSION_CODES)),
            ],
        }
        return render(request, self.template_name, context)

    @classmethod
    def _flatten(cls, by_code, codes):
        parts = []
        for code in codes:
            parts.extend(by_code.get(code, []))
        return parts

    @classmethod
    def _headline_specs(cls, vehicle, parts):
        specs: list[tuple[str, str, str | None]] = []
        seen: set[str] = set()

        def add(label, value, group=None):
            if not value or label in seen:
                return
            seen.add(label)
            specs.append((label, value, group))

        for part in parts:
            for raw_key, value in (part.specs or {}).items():
                normalized = str(raw_key).strip().lower()
                match = cls.HEADLINE_SPEC_LABELS.get(normalized)
                if match:
                    add(match[0], str(value).strip(), match[1])

        if vehicle.model.segment:
            add("Tipo", vehicle.model.segment)
        if vehicle.mileage:
            add("Kilometraje", f"{vehicle.mileage:,} km".replace(",", "."))
        if vehicle.color:
            add("Color", vehicle.color)
        return specs


class InternalVehicleListView(PermissionCodeRequiredMixin, ListView):
    permission_code = "vehicles.view"
    template_name = "vehicles/internal/vehicle_list.html"
    context_object_name = "vehicles"
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.has_perm_code("vehicles.view") and request.user.has_perm_code("vehicles.manage"):
            self.permission_code = "vehicles.manage"
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        self.search_form = VehicleSearchForm(self.request.GET, user=self.request.user)
        query = status = sort = ""
        branch = None
        if self.search_form.is_valid():
            query = self.search_form.cleaned_data.get("q", "")
            status = self.search_form.cleaned_data.get("status", "")
            branch = self.search_form.cleaned_data.get("branch")
            sort = self.search_form.cleaned_data.get("sort", "")
        return internal_vehicle_queryset(
            user=self.request.user,
            query=query,
            status=status,
            branch=branch,
            sort=sort,
            vin=self.search_form.cleaned_data.get("vin", ""),
            plate=self.search_form.cleaned_data.get("plate", ""),
            internal_code=self.search_form.cleaned_data.get("internal_code", ""),
            brand=self.search_form.cleaned_data.get("brand"),
            model=self.search_form.cleaned_data.get("model"),
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["search_form"] = self.search_form
        metrics = accessible_vehicle_queryset(self.request.user).aggregate(
            available=Count("id", filter=Q(status=Vehicle.Status.AVAILABLE)),
            reserved=Count("id", filter=Q(status=Vehicle.Status.RESERVED)),
            sold=Count("id", filter=Q(status=Vehicle.Status.SOLD)),
            hidden=Count("id", filter=Q(status=Vehicle.Status.HIDDEN)),
            archived=Count("id", filter=Q(status=Vehicle.Status.ARCHIVED)),
        )
        ctx["status_counts"] = {
            status: metrics[status]
            for status in ("available", "reserved", "sold", "hidden", "archived")
        }
        return ctx


class InternalVehicleCreateView(PermissionCodeRequiredMixin, CreateView):
    permission_code = "vehicles.manage"
    model = Vehicle
    form_class = VehicleForm
    template_name = "vehicles/internal/vehicle_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        try:
            self.object = create_vehicle(actor=self.request.user, form=form)
        except ValidationError as exc:
            form.add_error(None, exc.message if hasattr(exc, "message") else exc)
            return self.form_invalid(form)
        messages.success(self.request, "Vehículo creado correctamente.")
        return redirect("vehicles_internal:detail", pk=self.object.pk)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["mode"] = "create"
        ctx["page_heading"] = "Crear vehículo"
        return ctx


class InternalVehicleDetailView(PermissionCodeRequiredMixin, DetailView):
    permission_code = "vehicles.view"
    template_name = "vehicles/internal/vehicle_detail.html"
    context_object_name = "vehicle"

    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated and not request.user.has_perm_code("vehicles.view") and request.user.has_perm_code("vehicles.manage"):
            self.permission_code = "vehicles.manage"
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return vehicle_detail_queryset(self.request.user)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["media_upload_form"] = VehicleMediaUploadForm()
        ctx["link_codes"] = vehicle_link_codes_queryset(self.object)[:10]
        ctx["customer_links"] = vehicle_links_queryset(self.object)
        ctx["can_manage_link_codes"] = self.request.user.has_perm_code("vehicles.link_codes")
        ctx["garage_customer_choices"] = linkable_customer_queryset(user=self.request.user)[:100]
        return ctx


class InternalVehicleUpdateView(PermissionCodeRequiredMixin, DetailView):
    permission_code = "vehicles.manage"
    template_name = "vehicles/internal/vehicle_form.html"
    context_object_name = "vehicle"

    def get_queryset(self):
        return vehicle_detail_queryset(self.request.user, permission_codes=("vehicles.manage",))

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = VehicleForm(instance=self.object, user=request.user)
        return self.render_to_response(self.get_context_data(form=form, mode="update", page_heading="Editar vehículo"))

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = VehicleForm(request.POST, instance=self.object, user=request.user)
        if form.is_valid():
            try:
                self.object = update_vehicle(actor=request.user, vehicle=self.object, form=form)
            except ValidationError as exc:
                form.add_error(None, exc.message if hasattr(exc, "message") else exc)
                return self.render_to_response(
                    self.get_context_data(form=form, mode="update", page_heading="Editar vehículo")
                )
            messages.success(request, "Vehículo actualizado correctamente.")
            return redirect("vehicles_internal:detail", pk=self.object.pk)
        return self.render_to_response(self.get_context_data(form=form, mode="update", page_heading="Editar vehículo"))


class InternalVehicleStatusView(PermissionCodeRequiredMixin, View):
    permission_code = "vehicles.publish"

    def post(self, request, pk, action):
        vehicle = get_object_or_404(
            vehicle_detail_queryset(request.user, permission_codes=("vehicles.publish",)),
            pk=pk,
        )
        try:
            if action == "publish":
                publish_vehicle(vehicle=vehicle, actor=request.user)
                messages.success(request, "Vehículo publicado en el catálogo.")
            elif action == "hide":
                hide_vehicle(vehicle=vehicle, actor=request.user)
                messages.success(request, "Vehículo ocultado del catálogo público.")
            elif action == "archive":
                archive_vehicle(vehicle=vehicle, actor=request.user)
                messages.success(request, "Vehículo archivado correctamente.")
            else:
                messages.error(request, "Acción no válida.")
        except ValidationError as exc:
            messages.error(request, exc.message if hasattr(exc, "message") else str(exc))
        fallback = reverse("vehicles_internal:detail", kwargs={"pk": vehicle.pk})
        return redirect(safe_next_url(request, request.POST.get("next"), fallback))


class InternalVehicleMediaUploadView(PermissionCodeRequiredMixin, View):
    permission_code = "vehicles.manage"

    def post(self, request, pk):
        vehicle = get_object_or_404(
            vehicle_detail_queryset(request.user, permission_codes=("vehicles.manage",)),
            pk=pk,
        )
        form = VehicleMediaUploadForm(request.POST, request.FILES)
        if form.is_valid():
            upload_vehicle_media(actor=request.user, vehicle=vehicle, form=form)
            messages.success(request, "Multimedia cargada correctamente.")
        else:
            messages.error(request, "No se pudo cargar el archivo. Revisa extensión, tamaño y datos.")
        return redirect("vehicles_internal:detail", pk=vehicle.pk)


class _VehicleRelatedFormView(PermissionCodeRequiredMixin, View):
    """ES: Base con alcance para editar relaciones ordinarias del vehículo.

    EN: Scope-aware base for editing ordinary vehicle relations.
    """

    permission_code = "vehicles.manage"
    form_class = None
    relation_name = ""
    service = None
    service_argument = ""
    page_heading = "Editar dato del vehículo"
    template_name = "vehicles/internal/vehicle_related_form.html"

    def vehicle_or_404(self, request, pk):
        return get_object_or_404(
            vehicle_detail_queryset(request.user, permission_codes=("vehicles.manage",)),
            pk=pk,
        )

    def related_object(self, vehicle):
        item_pk = self.kwargs.get("item_pk")
        if item_pk is None:
            return None
        return get_object_or_404(getattr(vehicle, self.relation_name).all(), pk=item_pk)

    def render_form(self, request, vehicle, form):
        return render(
            request,
            self.template_name,
            {"vehicle": vehicle, "form": form, "page_heading": self.page_heading},
        )

    def get(self, request, pk, item_pk=None):
        vehicle = self.vehicle_or_404(request, pk)
        form = self.form_class(instance=self.related_object(vehicle))
        return self.render_form(request, vehicle, form)

    def post(self, request, pk, item_pk=None):
        vehicle = self.vehicle_or_404(request, pk)
        related = self.related_object(vehicle)
        form = self.form_class(request.POST, instance=related)
        if form.is_valid():
            try:
                kwargs = {
                    "actor": request.user,
                    "vehicle": vehicle,
                    "form": form,
                    self.service_argument: related,
                }
                self.service(**kwargs)
            except ValidationError as exc:
                form.add_error(None, exc.message if hasattr(exc, "message") else exc)
            else:
                messages.success(request, "Información del vehículo guardada correctamente.")
                return redirect("vehicles_internal:detail", pk=vehicle.pk)
        return self.render_form(request, vehicle, form)


class InternalVehicleHighlightFormView(_VehicleRelatedFormView):
    form_class = VehicleCommercialHighlightForm
    relation_name = "highlights"
    service = staticmethod(save_vehicle_highlight)
    service_argument = "highlight"
    page_heading = "Destacado comercial"


class InternalVehicleSpecificationFormView(_VehicleRelatedFormView):
    form_class = VehiclePartSpecificationForm
    relation_name = "part_specs"
    service = staticmethod(save_vehicle_part_specification)
    service_argument = "specification"
    page_heading = "Especificación técnica"


class InternalVehicleMediaEditView(_VehicleRelatedFormView):
    form_class = VehicleMediaMetadataForm
    relation_name = "media"
    service = staticmethod(update_vehicle_media)
    service_argument = "media"
    page_heading = "Metadatos multimedia"


class _VehicleRelatedDeleteView(PermissionCodeRequiredMixin, View):
    """ES: Elimina una relación acotada después de verificar alcance.

    EN: Deletes a scoped relation after verifying authorization scope.
    """

    permission_code = "vehicles.manage"
    relation_name = ""
    service = None
    service_argument = ""

    def post(self, request, pk, item_pk):
        vehicle = get_object_or_404(
            vehicle_detail_queryset(request.user, permission_codes=("vehicles.manage",)),
            pk=pk,
        )
        related = get_object_or_404(getattr(vehicle, self.relation_name).all(), pk=item_pk)
        self.service(actor=request.user, vehicle=vehicle, **{self.service_argument: related})
        messages.success(request, "Elemento desvinculado; la operación quedó auditada.")
        return redirect("vehicles_internal:detail", pk=vehicle.pk)


class InternalVehicleHighlightDeleteView(_VehicleRelatedDeleteView):
    relation_name = "highlights"
    service = staticmethod(remove_vehicle_highlight)
    service_argument = "highlight"


class InternalVehicleSpecificationDeleteView(_VehicleRelatedDeleteView):
    relation_name = "part_specs"
    service = staticmethod(remove_vehicle_part_specification)
    service_argument = "specification"


class InternalVehicleMediaDeleteView(_VehicleRelatedDeleteView):
    relation_name = "media"
    service = staticmethod(remove_vehicle_media)
    service_argument = "media"


class _VehicleLinkCodeScopedMixin:
    def vehicle_or_404(self, request, pk):
        return get_object_or_404(
            vehicle_detail_queryset(request.user, permission_codes=("vehicles.link_codes",)),
            pk=pk,
        )

    def link_code_or_404(self, vehicle, code_pk):
        return get_object_or_404(vehicle_link_codes_queryset(vehicle), pk=code_pk)

    def customer_link_or_404(self, vehicle, link_pk):
        return get_object_or_404(vehicle_links_queryset(vehicle), pk=link_pk)


class InternalVehicleLinkCodeGenerateView(PermissionCodeRequiredMixin, _VehicleLinkCodeScopedMixin, View):
    permission_code = "vehicles.link_codes"

    def post(self, request, pk):
        vehicle = self.vehicle_or_404(request, pk)
        expires_days = None
        try:
            expires_days = int(request.POST.get("expires_days", "") or "")
        except ValueError:
            expires_days = None
        if expires_days and not (1 <= expires_days <= 90):
            expires_days = None
        try:
            code_obj = generate_vehicle_link_code(actor=request.user, vehicle=vehicle, expires_after_days=expires_days)
        except ValidationError as exc:
            messages.error(request, exc.message if hasattr(exc, "message") else str(exc))
        else:
            messages.success(request, f"Código de vinculación generado: {code_obj.code}")
        return redirect("vehicles_internal:detail", pk=vehicle.pk)


class InternalVehicleLinkCodeRevokeView(PermissionCodeRequiredMixin, _VehicleLinkCodeScopedMixin, View):
    permission_code = "vehicles.link_codes"

    def post(self, request, pk, code_pk):
        vehicle = self.vehicle_or_404(request, pk)
        code_obj = self.link_code_or_404(vehicle, code_pk)
        try:
            revoke_vehicle_link_code(
                actor=request.user,
                link_code=code_obj,
                reason=request.POST.get("reason", "")[:220],
            )
        except ValidationError as exc:
            messages.error(request, exc.message if hasattr(exc, "message") else str(exc))
        else:
            messages.success(request, "Código revocado correctamente.")
        return redirect("vehicles_internal:detail", pk=vehicle.pk)


class InternalCustomerVehicleUnlinkView(PermissionCodeRequiredMixin, _VehicleLinkCodeScopedMixin, View):
    permission_code = "vehicles.link_codes"

    def post(self, request, pk, link_pk):
        vehicle = self.vehicle_or_404(request, pk)
        link = self.customer_link_or_404(vehicle, link_pk)
        try:
            unlink_customer_vehicle(
                actor=request.user,
                link=link,
                reason=request.POST.get("reason", "")[:220],
            )
        except ValidationError as exc:
            messages.error(request, exc.message if hasattr(exc, "message") else str(exc))
        else:
            messages.success(request, "Vinculación desactivada. El historial del vehículo se conserva.")
        return redirect("vehicles_internal:detail", pk=vehicle.pk)


class InternalVehicleTransferView(PermissionCodeRequiredMixin, _VehicleLinkCodeScopedMixin, View):
    permission_code = "vehicles.link_codes"

    def post(self, request, pk, link_pk):
        vehicle = self.vehicle_or_404(request, pk)
        link = self.customer_link_or_404(vehicle, link_pk)
        customer_qs = Customer.objects.filter(is_deleted=False)
        branch_ids = accessible_branch_ids(request.user, permission_codes=("customers.view", "customers.manage"))
        if branch_ids is not None:
            customer_qs = customer_qs.filter(assigned_branch_id__in=branch_ids)
        new_customer = get_object_or_404(customer_qs, pk=request.POST.get("customer"))
        try:
            transfer_customer_vehicle(
                actor=request.user,
                link=link,
                new_customer=new_customer,
                reason=request.POST.get("reason", "")[:220],
            )
        except ValidationError as exc:
            messages.error(request, exc.message if hasattr(exc, "message") else str(exc))
        else:
            messages.success(request, "Titularidad transferida. El historial técnico del vehículo se conserva.")
        return redirect("vehicles_internal:detail", pk=vehicle.pk)


class VehicleRedeemCodeView(LoginRequiredMixin, View):
    """Endpoint de canje de código privado para el portal del cliente.

    R06 entrega el endpoint canjeable; el portal completo (R07) lo consume
    dentro de su dashboard. El canje requiere la cuenta vinculada al
    expediente de cliente y el permiso `portal.access`.
    """

    template_name = "vehicles/redeem.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()
        if self._client_customer(request) is None:
            messages.error(
                request,
                "Tu cuenta no está vinculada a un expediente de cliente o no tiene acceso al garaje digital.",
            )
            return redirect("vehicles:catalog")
        return super().dispatch(request, *args, **kwargs)

    def _client_customer(self, request):
        if not request.user.has_perm_code("portal.access"):
            return None
        return Customer.objects.filter(account=request.user, is_deleted=False).first()

    def get(self, request):
        return redirect("portal:vehicle_redeem")

    def post(self, request):
        customer = self._client_customer(request)
        try:
            link = redeem_link_code(
                actor=request.user,
                customer=customer,
                code=request.POST.get("code", ""),
            )
        except ValidationError as exc:
            messages.error(request, exc.message if hasattr(exc, "message") else str(exc))
        else:
            messages.success(request, f"{link.vehicle} se agregó a tu garaje digital.")
            return redirect("portal:vehicle_detail", pk=link.pk)
        return redirect("portal:vehicle_redeem")


class VehicleCatalogDataView(PermissionCodeRequiredMixin, View):
    permission_code = "vehicles.manage"
    template_name = "vehicles/internal/catalog_data.html"

    def get(self, request):
        return render(
            request,
            self.template_name,
            {
                "brand_form": VehicleBrandForm(),
                "model_form": VehicleModelForm(),
                "brands": brand_list_queryset(),
                "models": model_list_queryset(),
            },
        )


class VehicleBrandCreateView(PermissionCodeRequiredMixin, View):
    permission_code = "vehicles.manage"

    def post(self, request):
        form = VehicleBrandForm(request.POST, request.FILES)
        if form.is_valid():
            create_brand(actor=request.user, form=form)
            messages.success(request, "Marca creada correctamente.")
        else:
            messages.error(request, "No se pudo crear la marca. Revisa los datos.")
        return redirect("vehicles_internal:catalog_data")


class VehicleModelCreateView(PermissionCodeRequiredMixin, View):
    permission_code = "vehicles.manage"

    def post(self, request):
        form = VehicleModelForm(request.POST)
        if form.is_valid():
            create_model(actor=request.user, form=form)
            messages.success(request, "Modelo creado correctamente.")
        else:
            messages.error(request, "No se pudo crear el modelo. Revisa los datos.")
        return redirect("vehicles_internal:catalog_data")
