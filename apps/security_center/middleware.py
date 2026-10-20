"""ES: Este módulo procesa controles transversales del ciclo HTTP para el dominio de seguridad.

EN: This module processes cross-cutting HTTP lifecycle controls for the security center domain.

Contexto existente / Existing context:
Request and response middleware for the security center domain.
"""

from __future__ import annotations

import secrets

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import logout
from django.core.exceptions import PermissionDenied, ValidationError
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.utils import timezone

from apps.security_center.models import SecurityPolicy
from apps.security_center.services import get_security_profile, password_is_expired, register_session
from apps.security_center.staff_access import (
    assess_staff_access,
    audit_monitored_staff_risk,
    ensure_staff_access_request,
)


class SecurityHeadersMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.csp_nonce = secrets.token_urlsafe(18)
        response = self.get_response(request)
        response.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
        response.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
        response.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        response.setdefault("Cross-Origin-Resource-Policy", "same-site")
        response.setdefault("X-Permitted-Cross-Domain-Policies", "none")
        response.setdefault(
            "Content-Security-Policy",
            "; ".join(
                [
                    "default-src 'self'",
                    "script-src 'self' https://unpkg.com",
                    f"style-src 'self' https://unpkg.com 'nonce-{request.csp_nonce}'",
                    "style-src-attr 'unsafe-inline'",
                    "img-src 'self' data: blob: https://api.maptiler.com",
                    "font-src 'self'",
                    "connect-src 'self' https://api.maptiler.com",
                    "media-src 'self' blob:",
                    "worker-src 'self' blob:",
                    "object-src 'none'",
                    "frame-src 'none'",
                    "frame-ancestors 'none'",
                    "base-uri 'self'",
                    "form-action 'self'",
                ]
            ),
        )
        return response


class SecurityEnforcementMiddleware:
    """ES: Agrupa el componente «security enforcement middleware» del dominio de seguridad y sus reglas relacionadas. Además, aplica autorización en backend, rechaza estados o entradas inválidas.

    EN: Groups the «security enforcement middleware» component and its related rules in the security center domain. It also enforces server-side authorization, rejects invalid input or state.
    """

    EXEMPT_PREFIXES = (
        "/static/",
        "/media/",
        "/accounts/login/",
        "/accounts/logout/",
        "/security/2fa/challenge/",
        "/security/2fa/setup/",
        "/security/password/change/",
    )

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        """ES: Ejecuta la operación «call» dentro del dominio de seguridad. Además, aplica autorización en backend, rechaza estados o entradas inválidas.

        EN: Executes the «call» operation within the security center domain. It also enforces server-side authorization, rejects invalid input or state.
        """

        if (
            not getattr(request, "user", None)
            or not request.user.is_authenticated
            or request.path.startswith(self.EXEMPT_PREFIXES)
        ):
            return self.get_response(request)

        policy = SecurityPolicy.current()
        now = timezone.now()
        last_activity = request.session.get("vinova_last_activity")
        if last_activity:
            try:
                previous = timezone.datetime.fromisoformat(last_activity)
                if timezone.is_naive(previous):
                    previous = timezone.make_aware(previous)
                if previous <= now - timezone.timedelta(minutes=policy.session_idle_minutes):
                    logout(request)
                    messages.warning(request, "Tu sesión terminó por inactividad.")
                    return redirect("accounts:login")
            except (TypeError, ValueError):
                pass
        request.session["vinova_last_activity"] = now.isoformat()

        tracked = register_session(request=request, user=request.user)
        if tracked.revoked_at:
            logout(request)
            messages.warning(request, "Esta sesión fue revocada por seguridad.")
            return redirect("accounts:login")
        absolute_minutes = max(1, int(getattr(settings, "VINOVA_SESSION_ABSOLUTE_MINUTES", 480)))
        if tracked.created_at <= now - timezone.timedelta(minutes=absolute_minutes):
            logout(request)
            messages.warning(request, "Tu sesión alcanzó su duración máxima.")
            return redirect("accounts:login")

        if request.user.must_change_password or password_is_expired(request.user, policy):
            messages.warning(request, "Debes actualizar tu contraseña antes de continuar.")
            return redirect("security_center:password_change")

        profile = get_security_profile(request.user)
        required = profile.is_two_factor_required(policy)
        if required and not profile.two_factor_enabled:
            messages.warning(request, "Tu cuenta administrativa debe configurar autenticación en dos pasos.")
            return redirect("security_center:two_factor_setup")
        if profile.two_factor_enabled and not request.session.get("vinova_2fa_verified"):
            request.session["vinova_2fa_next"] = request.get_full_path()
            return redirect("security_center:two_factor_challenge")

        try:
            assessment = assess_staff_access(request=request, policy=policy)
        except ValidationError:
            if policy.staff_access_mode == SecurityPolicy.StaffAccessMode.ENFORCE:
                if request.path.startswith("/api/"):
                    return JsonResponse({"detail": "La política de acceso Staff no está disponible."}, status=503)
                return HttpResponse("La política de acceso Staff requiere revisión administrativa.", status=503)
            assessment = None
        if assessment and assessment.monitored:
            audit_monitored_staff_risk(request=request, assessment=assessment)
        if assessment and not assessment.allowed:
            if not profile.two_factor_enabled:
                messages.warning(request, "Configura 2FA para solicitar acceso Staff fuera de la red habitual.")
                return redirect("security_center:two_factor_setup")
            try:
                access_request = ensure_staff_access_request(
                    request=request,
                    policy=policy,
                    assessment=assessment,
                )
            except PermissionDenied as exc:
                if request.path.startswith("/api/"):
                    return JsonResponse({"detail": str(exc)}, status=429)
                return HttpResponse(str(exc), status=429)
            request.session["vinova_staff_access_request_id"] = access_request.pk
            if request.path.startswith("/api/"):
                return JsonResponse(
                    {"detail": "Acceso Staff pendiente de aprobación.", "request_id": access_request.pk},
                    status=403,
                )
            return redirect("security_center:staff_access_pending")

        return self.get_response(request)
