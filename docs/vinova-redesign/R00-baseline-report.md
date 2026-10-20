# R00 — Baseline, alcance y protección de fuentes

- Fecha: 2026-10-08 03:44:47
- Rama: feature/v0-2-auth-roles (HEAD: ee657aa)
- Django check: OK (0 issues)
- Migraciones: sin cambios detectados
- Tests (no e2e): 2180 passed, 5 failed, 2 skipped (229s)
- Fallas conocidas (independientes del rediseño funcional): 
  - tests/security/test_d5_privilege_escalation.py::test_staff_without_roles_cannot_open_internal_pages[/nosotros/]
  - tests/security/test_d5_privilege_escalation.py::test_staff_without_roles_cannot_open_internal_pages[/servicios/]
  - apps/leads/tests/test_conversion_concurrency_v110.py::test_same_lead_creates_one_quote_and_one_conversion
  - apps/leads/tests/test_conversion_concurrency_v110.py::test_concurrent_leads_with_same_identity_reuse_customer
  - apps/leads/tests/test_conversion_concurrency_v110.py::test_concurrent_quotes_receive_distinct_numbers
- web_carros/: SOLO LECTURA (excluido de .git/info/exclude)
- AGENTS.md: fusionado Parte I + Parte B
- Inventario: 26 apps, 83 model classes (models.py), 199 url patterns, 174 templates, 40 css, 4 js, 115 test files

## Estado R00
- [x] Localización y protección
- [x] Fusión AGENTS.md
- [x] Baseline Django
- [x] Inventario inicial
- [x] docs/vinova-redesign + matrices (esqueleto)
- [ ] Auditoría exhaustiva R01 (pendiente)
