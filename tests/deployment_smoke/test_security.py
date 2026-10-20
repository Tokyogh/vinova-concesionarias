"""ES: Este módulo especifica regresiones ejecutables para el dominio de pruebas integrales.

EN: This module specifies executable regressions for the cross-domain tests domain.

Contexto existente / Existing context:
Regression coverage for security in the deployment_smoke domain.
"""

from __future__ import annotations

from tests.deployment_smoke.helpers.http import absolute, request
from tests.deployment_smoke.helpers.runtime import run_check

__test__ = False

SECURITY_HEADERS = {
    "x-content-type-options": "nosniff",
    "x-frame-options": "DENY",
    "referrer-policy": "strict-origin-when-cross-origin",
    "content-security-policy": "default-src",
    "permissions-policy": "camera=()",
    "cross-origin-opener-policy": "same-origin",
    "cross-origin-resource-policy": "same-site",
}


def run(state, session=None):  # noqa: ANN001
    config = state.config
    run_check(
        state,
        code="security.headers",
        scenario="security",
        title="Cabeceras de seguridad",
        callback=lambda: _headers(config.base_url, config.timeout_seconds, config.verify_tls),
    )
    run_check(
        state,
        code="security.protected_routes",
        scenario="security",
        title="Rutas privadas sin autenticación",
        callback=lambda: _protected_routes(config.base_url, config.timeout_seconds, config.verify_tls),
    )
    run_check(
        state,
        code="security.openapi_exposure",
        scenario="security",
        title="Exposición de Swagger y OpenAPI",
        callback=lambda: _api_docs(config.base_url, config.timeout_seconds, config.mode, config.verify_tls),
        required=False,
    )
    if session is not None:
        run_check(
            state,
            code="security.cookies",
            scenario="security",
            title="Cookies de sesión seguras",
            callback=lambda: _cookies(session, config.mode, config.allow_http_local),
        )
        run_check(
            state,
            code="security.private_download",
            scenario="security",
            title="Descargas privadas no expuestas directamente",
            callback=lambda: _private_download(session),
            required=False,
        )


def _headers(base_url: str, timeout: int, verify_tls: bool) -> dict:
    response = request(absolute(base_url, "/"), timeout=timeout, verify_tls=verify_tls)
    missing = []
    for name, expected_fragment in SECURITY_HEADERS.items():
        value = response.headers.get(name, "")
        if expected_fragment.lower() not in value.lower():
            missing.append(f"{name}={value!r}")
    if missing:
        raise AssertionError("Cabeceras faltantes o inválidas: " + "; ".join(missing))
    hsts = response.headers.get("strict-transport-security", "")
    result = {"headers_checked": sorted(SECURITY_HEADERS), "hsts": hsts}
    if not hsts:
        result.update(status="warning", message="HSTS no está activo; validar estrategia HTTPS definitiva del dominio.")
    return result


def _protected_routes(base_url: str, timeout: int, verify_tls: bool) -> dict:
    routes = [
        "/dashboard/",
        "/dashboard/documents/",
        "/dashboard/audit/",
        "/dashboard/company/",
    ]
    results = {}
    for path in routes:
        response = request(absolute(base_url, path), timeout=timeout, follow_redirects=False, verify_tls=verify_tls)
        results[path] = response.status
        if response.status not in {302, 303, 401, 403}:
            raise AssertionError(f"{path} quedó accesible sin autenticación: HTTP {response.status}.")
    return {"routes": results}


def _api_docs(base_url: str, timeout: int, mode: str, verify_tls: bool) -> dict:
    results = {}
    exposed = []
    for path in ["/api/schema/", "/api/docs/", "/api/v1/schema/", "/api/v1/docs/"]:
        response = request(absolute(base_url, path), timeout=timeout, follow_redirects=False, verify_tls=verify_tls)
        results[path] = response.status
        if response.status == 200:
            exposed.append(path)
    if exposed and mode == "production":
        return {
            "status": "warning",
            "message": "Swagger/OpenAPI está público en producción; confirmar que sea una decisión consciente.",
            "routes": results,
        }
    return {"routes": results}


def _cookies(session, mode: str, allow_http_local: bool = False) -> dict:  # noqa: ANN001
    assert session.context is not None
    cookies = session.context.cookies()
    session_names = {"sessionid", "__Host-vinova_session"}
    csrf_names = {"csrftoken", "__Host-vinova_csrf"}
    session_cookies = [cookie for cookie in cookies if cookie["name"] in session_names | csrf_names]
    if not session_cookies:
        raise AssertionError("No se encontraron cookies de sesión/CSRF tras el login.")
    problems = []
    insecure_local_cookies = []
    require_secure = mode == "production" and not allow_http_local
    for cookie in session_cookies:
        if require_secure and not cookie.get("secure"):
            problems.append(f"{cookie['name']} sin Secure")
        elif mode == "production" and allow_http_local and not cookie.get("secure"):
            insecure_local_cookies.append(cookie["name"])
        if cookie["name"] in session_names and not cookie.get("httpOnly"):
            problems.append(f"{cookie['name']} sin HttpOnly")
        if cookie["name"].startswith("__Host-") and (cookie.get("domain") or cookie.get("path") != "/"):
            problems.append(f"{cookie['name']} incumple el contrato __Host-")
        if str(cookie.get("sameSite", "")).lower() not in {"lax", "strict"}:
            problems.append(f"{cookie['name']} SameSite={cookie.get('sameSite')}")
    if problems:
        raise AssertionError("; ".join(problems))
    result = {
        "cookies": [
            {
                "name": cookie["name"],
                "secure": cookie.get("secure"),
                "http_only": cookie.get("httpOnly"),
                "same_site": cookie.get("sameSite"),
            }
            for cookie in session_cookies
        ]
    }
    if insecure_local_cookies:
        result.update(
            status="warning",
            message=(
                "Cookies Secure no exigidas por la excepción explícita --allow-http-local; "
                "deben validarse nuevamente sobre HTTPS en staging o producción."
            ),
            insecure_local_cookies=sorted(insecure_local_cookies),
        )
    return result


def _private_download(session) -> dict:  # noqa: ANN001
    assert session.page is not None
    page = session.goto("/dashboard/documents/")
    link = page.locator("a[href*='/dashboard/documents/'][href$='/download/']").first
    if link.count() == 0:
        return {"status": "skipped", "message": "No existen documentos privados visibles para probar descarga.", "required": False}
    download_url = link.get_attribute("href") or ""
    context = session.browser.new_context(ignore_https_errors=not session.verify_tls)  # type: ignore[union-attr]
    try:
        response = context.request.get(session.url(download_url), max_redirects=0, timeout=session.timeout_ms)
        if response.status not in {302, 303, 401, 403}:
            raise AssertionError(f"Descarga privada accesible sin sesión: HTTP {response.status}.")
        return {"status_code": response.status}
    finally:
        context.close()
