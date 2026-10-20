"""ES: Este módulo implementa el componente generate asvs matrix para el dominio de operación y QA.

EN: This module implements the generate asvs matrix component for the operations and QA domain.

Contexto existente / Existing context:
Genera la matriz trazable ASVS 5.0.0 para VINOVA PRO.

Generates the traceable ASVS 5.0.0 matrix for VINOVA PRO.

La fuente oficial está fijada por versión y SHA-256. El generador es
deliberadamente conservador: solo marca como verificados controles con prueba
directa; el resto permanece parcial, no conforme o pendiente externo.

The official source is pinned by version and SHA-256. The generator is
deliberately conservative: only controls with direct tests are marked as
verified; everything else remains partial, non-compliant, or externally pending.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import urllib.request
from pathlib import Path


ASVS_URL = (
    "https://raw.githubusercontent.com/OWASP/ASVS/v5.0.0_release/5.0/docs_en/"
    "OWASP_Application_Security_Verification_Standard_5.0.0_en.json"
)
ASVS_SHA256 = "bcdbec214d70abcfad9284a31d4f9e5134305831d628aad3aa85d7e26626cb35"

FIELDS = (
    "id_oficial",
    "nivel",
    "capitulo",
    "seccion",
    "requisito_oficial",
    "aplicabilidad",
    "componente",
    "control_implementado",
    "evidencia",
    "prueba",
    "resultado",
    "brecha",
    "accion",
    "riesgo_residual",
)

COMPONENTS = {
    "V1": "Forms, serializers, templates, selectors y servicios",
    "V2": "Forms, modelos y servicios de dominio",
    "V3": "Templates, JavaScript, CSP y cabeceras",
    "V4": "DRF, API v1, scopes, webhooks e idempotencia",
    "V5": "Uploads, imports, documents y storages",
    "V6": "accounts y security_center",
    "V7": "Sesiones Django y SecurityEnforcementMiddleware",
    "V8": "PermissionCode, scopes, ownership y sucursales",
    "V9": "Tokens autocontenidos",
    "V10": "OAuth/OIDC",
    "V11": "Cifrado, hashing, TOTP y secretos",
    "V12": "Nginx, TLS y conexiones externas/internas",
    "V13": "Settings, Docker, Nginx y secretos de despliegue",
    "V14": "Privacidad, documentos, exports y retención",
    "V15": "Arquitectura Django, servicios y concurrencia",
    "V16": "AuditLog, logging, alertas y manejo de errores",
    "V17": "WebRTC",
}

EVIDENCE = {
    "V1": "apps/common/validators.py; templates/; apps/*/forms.py; apps/*/api/serializers.py",
    "V2": "apps/*/services.py; constraints de modelos; tests de dominio",
    "V3": "apps/security_center/middleware.py; templates/; static/js/",
    "V4": "apps/api/; apps/*/api/; docs/API.md",
    "V5": "apps/common/validators.py; apps/imports/parsing.py; apps/continuity/archive.py; apps/documents/",
    "V6": "apps/accounts/; apps/security_center/",
    "V7": "apps/security_center/middleware.py; apps/security_center/models.py",
    "V8": "apps/accounts/scopes.py; apps/accounts/models.py; docs/RBAC.md",
    "V9": "No se emiten tokens autocontenidos para autenticación",
    "V10": "No existe flujo OAuth/OIDC en urls, settings ni dependencias",
    "V11": "apps/security_center/crypto.py; apps/security_center/totp.py; hashers Django",
    "V12": "config/settings/production.py; docker/nginx/",
    "V13": "config/settings/; compose.yaml; Dockerfile; scripts/check_staging_env.py",
    "V14": "apps/privacy/; apps/documents/; apps/audit/",
    "V15": "apps/*/services.py; select_for_update; constraints e idempotencia",
    "V16": "apps/audit/; config/settings/base.py; tests/security/test_d5_audit_resilience.py",
    "V17": "No existen componentes WebRTC",
}

TESTS = {
    "V1": "tests/security/test_d5_defensive_controls.py; apps/common/tests/test_upload_content_validation.py",
    "V2": "tests/security/test_d7_role_action_sweep.py; pruebas unitarias por dominio",
    "V3": "apps/common/tests/test_http_security_v170.py; tests/security/test_d5_csrf.py",
    "V4": "apps/api/tests/test_api_integrations_bi_v021.py; apps/accounts/tests/test_api_scope_v170.py",
    "V5": "apps/documents/tests/test_uploads_security.py; apps/common/tests/test_upload_content_validation.py; apps/continuity/tests/test_transfer.py",
    "V6": "apps/security_center/tests/test_security_center.py; apps/accounts/tests/test_client_access.py",
    "V7": "apps/security_center/tests/test_security_center.py; tests/security/test_d5_anonymous_surface.py",
    "V8": "tests/security/test_integral_rbac_matrix.py; tests/security/test_d5_authorization_matrix.py",
    "V9": "Revisión estática de mecanismos de token",
    "V10": "Revisión estática de rutas, settings y dependencias",
    "V11": "apps/security_center/tests/test_security_center.py",
    "V12": "apps/security_center/tests/test_deployment_checks_v170.py; validación Nginx local",
    "V13": "tests/security/production_settings_probe.py; check --deploy",
    "V14": "apps/privacy/tests/; apps/documents/tests/; tests/security/test_d5_information_exposure.py",
    "V15": "pruebas PostgreSQL/concurrencia y servicios de dominio",
    "V16": "tests/security/test_d5_audit_resilience.py; apps/common/tests/test_logging_security_v170.py",
    "V17": "Revisión estática de componentes",
}

VERIFIED = {
    "V1.1.2", "V1.2.1", "V1.2.2", "V1.2.4",
    "V5.2.1", "V5.2.2", "V5.2.3", "V5.3.2",
    "V6.2.1", "V6.2.2", "V6.2.3", "V6.2.4", "V6.2.6", "V6.2.7", "V6.2.8", "V6.2.9",
    "V6.3.1", "V6.4.1", "V6.4.2", "V6.5.1", "V6.5.2", "V6.5.3", "V6.5.5",
    "V7.2.1", "V7.2.2", "V7.2.3", "V7.2.4", "V7.4.1", "V7.4.4", "V7.4.5", "V7.5.2",
    "V8.1.1", "V8.1.2", "V8.2.1", "V8.2.2", "V8.2.3", "V8.3.1",
    "V13.4.2", "V13.4.5", "V16.5.1",
}

NOT_APPLICABLE_CHAPTERS = {"V9", "V10", "V17"}
NOT_APPLICABLE = {
    "V1.2.6", "V1.2.7", "V1.2.8", "V1.3.1", "V1.3.4", "V1.3.5", "V1.3.8", "V1.3.9",
    "V6.8.1", "V6.8.2", "V6.8.3", "V6.8.4", "V7.1.3", "V7.6.1", "V8.4.1", "V12.1.3",
}

NON_COMPLIANT = {
    "V5.4.3": (
        "No existe antivirus/CDR para archivos de fuentes no confiables.",
        "Definir cuarentena y proveedor de escaneo; bloquear publicación/descarga hasta resultado seguro.",
        "Alto",
    ),
    "V6.1.2": (
        "No existe lista documentada de palabras contextuales.",
        "Definir lista empresarial sin datos sensibles e integrarla al validador.",
        "Medio",
    ),
    "V6.2.5": (
        "La política actual puede exigir clases de caracteres, contrario al requisito ASVS 5.0.0.",
        "Migrar a longitud y bloqueo de contraseñas comunes/comprometidas sin reglas de composición.",
        "Medio",
    ),
    "V6.2.10": (
        "La política activa usa caducidad periódica de contraseña por defecto.",
        "Desactivar rotación periódica y exigir cambio solo ante compromiso o evento de riesgo.",
        "Medio",
    ),
    "V6.2.11": (
        "No se aplica una lista empresarial de términos fáciles de adivinar.",
        "Añadir validación contextual versionada y pruebas.",
        "Medio",
    ),
    "V6.2.12": (
        "No se comprobó un corpus de contraseñas filtradas/comprometidas.",
        "Evaluar corpus local o servicio k-anonymity con privacidad y disponibilidad controladas.",
        "Alto",
    ),
    "V6.3.3": (
        "MFA es configurable y no obligatorio para todo acceso de nivel ASVS L2.",
        "Aplicar MFA por riesgo y para Staff sin bloquear administradores; documentar excepción de clientes.",
        "Alto",
    ),
    "V13.3.1": (
        "Los secretos usan variables de entorno, pero no se verificó un vault con ciclo de vida.",
        "Integrar gestor de secretos en staging/producción y probar rotación/revocación.",
        "Alto",
    ),
    "V16.4.3": (
        "No se verificó transmisión de logs a un sistema separado e inmutable.",
        "Configurar sink externo con TLS, control de acceso, alertas y retención.",
        "Alto",
    ),
}

EXTERNAL_PREFIXES = ("V12.",)
EXTERNAL_IDS = {"V13.2.1", "V13.2.2", "V13.2.3", "V16.2.2"}

RISK_BY_CHAPTER = {
    "V1": "Alto", "V2": "Alto", "V3": "Alto", "V4": "Alto", "V5": "Alto", "V6": "Crítico",
    "V7": "Crítico", "V8": "Crítico", "V11": "Alto", "V12": "Alto", "V13": "Alto",
    "V14": "Alto", "V15": "Alto", "V16": "Alto",
}


def _load_source(path: Path | None) -> dict:
    """ES: Carga y verifica la fuente. EN: Loads and verifies the source."""

    payload = path.read_bytes() if path else urllib.request.urlopen(ASVS_URL, timeout=30).read()  # noqa: S310
    digest = hashlib.sha256(payload).hexdigest()
    if digest != ASVS_SHA256:
        raise SystemExit(f"ASVS source checksum mismatch: {digest}")
    data = json.loads(payload)
    if data.get("Version") != "5.0.0":
        raise SystemExit("Unexpected ASVS version")
    return data


def _base_row(chapter: dict, section: dict, requirement: dict) -> dict[str, str]:
    chapter_id = chapter["Shortcode"]
    requirement_id = requirement["Shortcode"]
    return {
        "id_oficial": f"v5.0.0-{requirement_id[1:]}",
        "nivel": f"L{requirement['L']}",
        "capitulo": chapter["Name"],
        "seccion": section["Name"],
        "requisito_oficial": requirement["Description"],
        "aplicabilidad": "Aplicable",
        "componente": COMPONENTS[chapter_id],
        "control_implementado": "Existe una base de control; falta completar verificación individual contra el texto oficial.",
        "evidencia": EVIDENCE[chapter_id],
        "prueba": TESTS[chapter_id],
        "resultado": "Parcial",
        "brecha": "No se ha demostrado todavía la totalidad del requisito con evidencia requisito-específica.",
        "accion": "Crear o enlazar una prueba requisito-específica y revisar configuración de staging cuando corresponda.",
        "riesgo_residual": RISK_BY_CHAPTER.get(chapter_id, "Bajo"),
    }


def _classify(row: dict[str, str], chapter_id: str, requirement_id: str) -> None:
    """ES: Aplica estados conservadores. EN: Applies conservative statuses."""

    if chapter_id in NOT_APPLICABLE_CHAPTERS or requirement_id in NOT_APPLICABLE:
        row.update(
            aplicabilidad="No aplicable",
            control_implementado="El componente o protocolo descrito no forma parte de VINOVA PRO.",
            resultado="No aplica justificado",
            brecha="Ninguna mientras el componente permanezca ausente.",
            accion="Reevaluar si se incorpora el componente, protocolo o modelo de despliegue.",
            riesgo_residual="Bajo",
        )
        return
    if requirement_id in NON_COMPLIANT:
        gap, action, risk = NON_COMPLIANT[requirement_id]
        row.update(
            control_implementado="El control requerido no está implementado o no fue verificado de forma suficiente.",
            resultado="No cumple",
            brecha=gap,
            accion=action,
            riesgo_residual=risk,
        )
        return
    if requirement_id in VERIFIED:
        row.update(
            control_implementado="Control implementado en backend/configuración y cubierto por regresión automatizada.",
            resultado="Cumple verificado",
            brecha="Sin brecha local reproducible; permanece la validación del entorno cuando aplique.",
            accion="Conservar regresión y volver a verificar ante cambios del componente.",
            riesgo_residual="Bajo",
        )
        return
    if requirement_id in EXTERNAL_IDS or requirement_id.startswith(EXTERNAL_PREFIXES):
        row.update(
            control_implementado="Existe configuración local, pero el requisito depende del entorno o proveedor real.",
            resultado="Pendiente de proveedor o infraestructura",
            brecha="No se verificó el control extremo a extremo en infraestructura candidata.",
            accion="Validar en staging con evidencia de red, certificados, identidad de servicio y monitoreo.",
            riesgo_residual="Alto",
        )


def build_rows(data: dict) -> list[dict[str, str]]:
    """ES: Aplana L1/L2. EN: Flattens L1/L2 requirements."""

    rows: list[dict[str, str]] = []
    for chapter in data["Requirements"]:
        for section in chapter["Items"]:
            for requirement in section["Items"]:
                if int(requirement["L"]) > 2:
                    continue
                row = _base_row(chapter, section, requirement)
                _classify(row, chapter["Shortcode"], requirement["Shortcode"])
                rows.append(row)
    if len(rows) != 253:
        raise SystemExit(f"Unexpected L1/L2 requirement count: {len(rows)}")
    return rows


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, help="Optional local copy of the pinned official JSON")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("docs/seguridad-avanzada/04-matriz-asvs-5.0.0.csv"),
    )
    args = parser.parse_args()
    rows = build_rows(_load_source(args.source))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["resultado"]] = counts.get(row["resultado"], 0) + 1
    print(json.dumps({"total": len(rows), "results": counts}, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
