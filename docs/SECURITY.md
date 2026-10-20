# VINOVA SECURITY
Always: VALIDATE+AUTHENTICATE+AUTHORIZE+ISOLATE+LIMIT+AUDIT. External input=untrusted; frontend!=security boundary.

INPUT: validate type/length/format/range/allowlist/relations/state/permissions via Forms/DRF serializers/model/domain validators. Backend validation mandatory.

SQLI: prefer ORM. Never concatenate user input into SQL. Raw SQL only parameterized,minimal,justified,tested.

XSS: keep autoescape. Audit |safe/mark_safe. No arbitrary user HTML. Rich text only strict allowlist sanitization. Safe JS serialization/json_script. No eval/new Function on external data.

CSP: progressive strict allowlists; prefer local assets. Avoid unsafe-eval/wildcards; reduce unsafe-inline without breaking HTMX/Alpine. Test before enforcing.

CORS: production explicit allowlist from config/env; never CORS_ALLOW_ALL_ORIGINS=True. CORS != auth/security against curl/Python.

CSRF: keep enabled for Django sessions. Audit csrf_exempt; only justified exceptions. Configure trusted origins/Secure/SameSite/HTTPS.

RATE LIMIT: prioritize login,password recovery,public endpoints,signup,API,expensive search,uploads,exports,campaigns,sensitive actions. Scope by IP/user/auth state/endpoint as appropriate; Redis shared backend when useful; return 429; don't block normal usage.

BRUTE FORCE: throttling/rate-limit/backoff/temp lock/audit as appropriate; avoid unnecessary account enumeration.

SESSIONS/COOKIES: production Secure,HttpOnly,SameSite,HTTPS,reasonable expiry/rotation. Avoid sensitive tokens in localStorage unless strongly justified.

AUTHZ/IDOR: knowing ID never grants access. Fetch sensitive objects through authorized scoped querysets. Apply branch/user/role/permission/ownership/state. Regression test real IDOR fixes.

MASS ASSIGNMENT: client must not freely set branch,owner,created_by,approved_by,status,totals,balance,role,permissions,audit fields. Avoid blind fields="__all__" on sensitive APIs.

FILES: validate size,MIME,extension,name,destination; don't trust extension only. Prevent traversal,overwrite,execution,public leakage. Private docs require authorization.

PATH: normalize and ensure final path remains inside allowed root.

SSRF: external URL fetch must block loopback/private/internal/cloud metadata/dangerous schemes; prefer allowlists.

COMMAND: no shell concatenation with input. Prefer Python APIs; if subprocess: shell=False,separate args,allowlist.

DESERIALIZATION: no pickle/untrusted executable formats; prefer JSON/explicit serializers.

REDIRECTS: validate next/redirect target; no arbitrary external redirects.

HTTPS/HEADERS: production HTTPS, DEBUG=False; configure HSTS,X-Content-Type-Options,Referrer-Policy,frame protection,CSP as appropriate; no stack traces to users.

API: explicit auth,permissions,methods,serializers,scopes,throttling,pagination/limits. No convenience CRUD that bypasses business services. Critical operations reuse services.

DATA MINIMIZATION: serializers/responses expose only necessary fields; never leak hashes,tokens,secrets,private/internal metadata.

LOGGING: never log passwords,tokens,cookies full,Authorization,secrets,unneeded private data. Log relevant actor/action/time/resource/result/security events.

AUDIT: protect trail for login,security changes,roles/perms,sales,reservations,payments,reversals,discounts,inventory,sensitive exports,config,campaigns. Normal users cannot arbitrarily rewrite audit.

HTMX: same backend auth/permission/scope/validation as full views. Hidden/disabled UI != protection.

FEATURE OFF: must block direct URL/API/HTMX/tasks/exports/actions/notifs, not only hide menu.

RLS: defense-in-depth only, NOT tenancy. Candidate sensitive tables: sales,payments,customers,documents,financial movements. Django scopes remain mandatory. Before enable: audit DB user/connection/context,branch/user context,Celery,commands,migrations,tests/pooling. Incremental; never mass-enable blindly.

DB LEAST PRIVILEGE: runtime app user ideally non-superuser and only required privileges. If RLS used, runtime must not BYPASSRLS. Separate schema/migration owner when practical; don't destructively change real credentials.

DEPENDENCIES: minimal,maintained,controlled updates; security review; no unrelated major upgrades.

SECURITY TESTS: when relevant test IDOR,branch isolation,roles/expiry,CSRF,API methods,invalid input,XSS,uploads,feature OFF,rate-limit,state rules,concurrency.

DEFENSE DEPTH: Nginx→HTTPS/headers/limits→Django→auth→permissions→capabilities→branch scope→validation→services→transactions→DB constraints/RLS→audit.

Assume attacker can forge HTTP,change IDs,replay/concurrently send requests,send HTML/JS/SQL/path payloads,use unexpected methods. Critical operation must remain safe without trusting frontend.

## Estado comprobado

Esta guía define el contrato de ingeniería. La implementación actual comprobada
incluye CSRF, autoescape, CSP con nonce, cookies productivas `__Host-`, rotación
y revocación de sesiones, scopes RBAC, ownership, throttling, acceso Staff
adaptativo, consentimiento previo, validación/límites de archivos, storage
privado, destino DNS fijado para webhooks, auditoría encadenada y redacción de
secretos.

La evaluación usa CIA y STRIDE para amenazas, OWASP ASVS 5.0 con objetivo L2
para trazabilidad y OWASP Top 10/API Top 10/CWE como referencias
complementarias. La [matriz ASVS](seguridad-avanzada/04-matriz-asvs.md) conserva
estados `Cumple verificado`, `Parcial`, `No cumple` y `No aplica`; ningún control
se considera cerrado por documentación solamente.

Se cerraron localmente los riesgos antes registrados de DNS rebinding entre
validación y envío, ausencia de lock con hashes y `style-src 'unsafe-inline'`.
Permanece una excepción acotada en `style-src-attr`, y siguen pendientes
antivirus/CDR, egreso de red, vault/HSM, firma/attestation del artefacto,
proveedores, DNS/TLS y restauración real. El índice de evidencia vigente está en
[`seguridad-avanzada/ESTADO_ACTIVO.md`](seguridad-avanzada/ESTADO_ACTIVO.md).

Estos controles no demuestran seguridad absoluta ni cumplimiento legal
definitivo.
