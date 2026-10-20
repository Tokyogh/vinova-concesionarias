# F4 — matriz OWASP ASVS 5.0.0

Fecha: 2026-10-15

## Fuente y alcance

Se utilizó la versión estable oficial **OWASP ASVS 5.0.0**, publicada en mayo de 2025. La fuente está fijada al tag `v5.0.0_release` y al SHA-256:

`bcdbec214d70abcfad9284a31d4f9e5134305831d628aad3aa85d7e26626cb35`

Referencias:

- [Proyecto ASVS](https://owasp.org/projects/asvs/)
- [Release estable 5.0.0](https://github.com/OWASP/ASVS/releases/tag/v5.0.0_release)
- [JSON oficial utilizado](https://github.com/OWASP/ASVS/blob/v5.0.0_release/5.0/docs_en/OWASP_Application_Security_Verification_Standard_5.0.0_en.json)

La matriz completa está en [`04-matriz-asvs-5.0.0.csv`](04-matriz-asvs-5.0.0.csv). Contiene los **253 requisitos L1/L2** y, por cada uno: identificador versionado, nivel, texto oficial, aplicabilidad, componente, control, evidencia, prueba, resultado, brecha, acción y riesgo residual.

## Resultado inicial

| Estado | Requisitos | Interpretación |
|---|---:|---|
| Cumple verificado | 40 | existe evidencia local y regresión automatizada directa |
| Parcial | 133 | hay base de control, pero falta demostrar el requisito completo de manera individual |
| No cumple | 9 | brecha concreta identificada |
| No aplica justificado | 59 | componente ausente: por ejemplo OAuth/OIDC, tokens autocontenidos, WebRTC o tecnología específica |
| Pendiente de proveedor o infraestructura | 12 | TLS, identidad de servicio, sincronización u otro control no demostrable solo en local |
| **Total** | **253** | objetivo L1/L2 inventariado; no equivale a cumplimiento global |

## Incumplimientos demostrados

1. `v5.0.0-5.4.3`: no existe antivirus/CDR para archivos externos.
2. `v5.0.0-6.1.2`: no existe lista documentada de palabras contextuales prohibidas.
3. `v5.0.0-6.2.5`: la política puede exigir composición de contraseña.
4. `v5.0.0-6.2.10`: existe caducidad periódica por defecto.
5. `v5.0.0-6.2.11`: no se aplica lista contextual empresarial.
6. `v5.0.0-6.2.12`: no se comprobó un corpus de contraseñas comprometidas.
7. `v5.0.0-6.3.3`: MFA no es obligatorio para todo acceso L2.
8. `v5.0.0-13.3.1`: no se verificó un vault con ciclo de vida de secretos.
9. `v5.0.0-16.4.3`: no se verificó un sistema separado e inmutable de logs.

F6–F8 pueden corregir de forma segura la composición/rotación y elevar MFA para Staff. Antivirus, vault, sink de logs y validación TLS requieren decisiones o infraestructura externa; no se simularán como resueltos.

## Criterio conservador

- No se infiere cumplimiento por usar Django o una librería.
- Un test general no convierte automáticamente todos los requisitos de un capítulo en “Cumple verificado”.
- “No aplica” se limita a tecnologías realmente ausentes y debe revisarse si cambia la arquitectura.
- Los 134 parciales forman un backlog verificable, no una afirmación de fallo explotable.
- Los textos oficiales se conservan en inglés para evitar alterar su significado normativo.

## Reproducción

```powershell
python scripts/generate_asvs_matrix.py
```

El generador descarga únicamente la fuente oficial fijada, valida versión/checksum y falla si el número L1/L2 deja de ser 253. La salida es determinista y no contiene secretos ni datos personales.
