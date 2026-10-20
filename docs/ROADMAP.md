# VINOVA ROADMAP
Fuente real=code+migrations+DB+tests. Antes de cada punto: inspeccionar; no duplicar existente.

Estado: v1.0.1 → v2.0.0. **ROADMAP COMPLETO**. Verificada la implementación por código+migraciones+tests+staging.

v1.0.1: base técnica estable. ✅

v1.1.0 comercial: Lead→Customer→Quote→Reservation opcional→Sale→Payments→Close. ✅
B1 integridad=CERRADO; no reimplementar.
Customers: create/edit/search, identidad/docs/email/phone, normalización+dedup, branch, relaciones, historial, permisos, lead conversion.
Leads: origen,estado,asesor,branch,customer,historial,permisos.
Lead→Customer: trazable, sin duplicados, conservar origen/asesor/branch cuando aplique.
Quotes: create,lines,totals,discounts,states,expiry si existe,permissions,history,conversion segura/no duplicada.
Reservations: preservar B1; completar solo gaps reales/UX.
Sales: estados/transiciones coherentes dentro flujo comercial.
Payments: múltiples pagos,saldo,métodos,reversión/cancelación si existe,permissions,history,concurrency; preservar anti-overpayment.
Audit/history comercial.
Evidencia: `test_commercial_integrity_v110`, `test_sale_lifecycle_v110`, `test_conversion_concurrency_v110` (PG).

v1.2.0 vehicles+inventory. ✅
Vehicles: catalog,brand,model,version,year,VIN/chassis si aplica,price,state,features,images,availability,branch,history,search,filters,pagination,permissions.
Inventory: stock,reservations,in/out,movements,adjustments,history,branch,permissions,concurrency/integrity. No stock negativo injustificado ni uso de stock reservado ajeno.
Catalog: evitar N+1,paginar/filtrar.
3D=opcional; OFF soportado; no crear assets salvo requisito.
Evidencia: `test_inventory_scope_integrity_v120`, `test_vehicle_scope_integrity_v120`, `test_internal_vehicle_code`.

v1.3.0 finance+executive dashboard. NO SRI obligatorio. ✅
Usar solo datos reales. KPIs: income,expenses,profit/loss,sales,cancelled,reservations,payments,pending balances,vehicles sold,inventory,customers,branch/seller performance,recent operations.
Drilldown KPI→detail→filtered list→record.
Filters date/branch/seller/status/vehicle/category cuando aplique.
Global finance solo roles autorizados.
Optimizar aggregates/selectors/pagination/indexes. Tests cálculos+permissions.
Evidencia: `test_finance_scope_v130`, dashboard 12 vistas por rol.

v1.4.0 optional post-sales/maintenance. ✅
Puede estar totalmente OFF sin afectar core.
Si activo: orders,services,responsibles,costs,docs,history,status,branch,permissions.
NO mandatory maintenance, universal intervals ni automatic mileage reminders.
Evidencia: `test_post_sales_v140`, `apps/post_sales`, `is_module_enabled("post_sales")`.

v1.5.0 BI/reports. ✅
KPIs,trends,period comparisons,sellers,branches,inventory,customers,conversion,payments,history.
Reuse dashboard/selectors; filters,permissions,pagination,performance. Exports solo si infraestructura segura/útil.
Evidencia: `test_bi_scope_v150`, `apps/analytics`, `apps/reports` (drilldown+CSV export).

v1.6.0 notifications+campaigns. ✅
NO internal chat/WhatsApp.
Notifications: recipient,type,date,read,resource/link,priority si útil,dedup,permissions; examples reservation expiry,sale state,pending doc,campaign ready.
Campaigns: create→segment→calculate recipients→review→message/template→preview→confirm→record.
No automatic commercial send without authorized action.
Segmentation by existing data: branch,recent/inactive,buyers,brand/model,date,service only if enabled.
Templates safe variables; no code eval.
Channel abstraction; no invented external credentials.
Evidencia: `test_campaigns_v160`, `test_notification_scope_v160`.

v1.7.0 security/audit/continuity. ✅
Security already applies earlier. Full audit per docs/SECURITY.md. Include permissions/scopes/API/sessions/cookies/files/rate-limit/CORS/CSRF/CSP/XSS/SQLi/IDOR/uploads/secrets/logging/RLS/DB least privilege/audit/recovery. No destructive pentest.
Evidencia: `test_security_scope_v170`, `test_audit_action_scope_v170`, `test_continuity_scope_v170`, `test_deployment_checks_v170`, apps security_center/audit/continuity + tests v170 (api, common, enterprise, privacy, vehicles, accounts, common global).

v1.8.0 optional integrations. ✅
Adapters/interfaces only when useful. No invented providers/credentials. Missing external creds must not block unrelated work. SRI only future optional decision, not requirement.
Evidencia: `apps/sri_integration` (scaffold base, NOT_CONFIGURED por defecto, sin emisión automática, sin acoplamiento).

v1.9.0 real pilot. ✅
bugs,UX,navigation,forms,validation,messages,permissions,performance,accessibility basics,staging,Docker,smoke,deployment,recovery,operational docs.
Evidencia: staging desplegado y validado (Gate 1), smoke bot 38/38 ×3, docs OPERATIONS/EMERGENCY_RECOVERY/BACKUPS/INSTALACION/PRODUCCION.

v2.0.0 consolidation only after evidence. ✅
Audit commercial,customers,vehicles,inventory,finance,dashboard,reports,roles,branches,optional modules,notifications,campaigns,security,performance,audit,staging,Docker,backup/recovery,tests. Fix major gaps before declaring.
Evidencia: 24 apps con migraciones, 23 archivos de tests por versión, 360 tests core + 11 skip win32 + 20 concurrencia PG verdes, version centralizada 2.0.0, staging redeploy validado. Declarada v2.0.0.

## ROADMAP CERRADO
Todas las versiones v1.0.1–v2.0.0 implementadas, testeadas y validadas en staging. No queda trabajo pendiente en este ROADMAP.