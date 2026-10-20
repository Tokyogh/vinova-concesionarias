# F17.1–F17.4 — Diagnóstico de contacto y solicitudes

Fecha: 2026-10-18

## Resultado reproducido

| Hallazgo | Estado previo | Causa raíz | Decisión aplicada |
|---|---|---|---|
| teléfono alfabético en perfil cliente | confirmado | `PortalCustomerProfileForm` no usaba el validador común | teléfono y WhatsApp usan la validación compartida y `inputmode=tel` |
| teléfono alfabético en solicitud de privacidad | confirmado | los formularios público e interno confiaban solo en `max_length` | validación telefónica, de nombre, controles invisibles y canal de entrada |
| contacto inválido en clientes, leads, registro, APIs e imports | no reproducido en las capas revisadas | ya reutilizaban `validate_phone_number` | se conservaron los controles; se añadió un auditor heredado de solo lectura |
| obligatoriedad inconsistente | confirmado en selección de canal | se podía elegir teléfono, WhatsApp o correo sin proporcionar ese dato | solo el canal elegido se vuelve obligatorio; el contacto presencial sigue sin exigir teléfono |
| monto `5 usd` | ya rechazado | `DecimalField` de Django ya impedía texto | se añadió límite técnico acorde con `max_digits`, dos decimales y ayuda visible |
| montos sin límite superior explícito | confirmado | el formulario dependía del límite implícito del modelo | límite explícito `9.999.999.999,99`, sin inventar mínimos comerciales |

## Decisiones de operación

- El registro de cuenta conserva nombres, apellidos, correo y contraseña como obligatorios; el teléfono sigue opcional.
- El perfil cliente no exige completar dirección, ciudad y provincia para navegar. Exige únicamente el dato del canal preferido.
- Una solicitud comercial pública es captura de interés, no una oferta contractual ni una venta. Permanece disponible sin autenticación, con rate limiting, consentimiento y validación en backend.
- `budget_min` y `budget_max` son preferencias referenciales en USD. No crean reservas, cotizaciones ni pagos.
- Ventas y facturación mantienen sus propios requisitos transaccionales; no se relajaron.
- Los registros heredados se inspeccionan con `python manage.py audit_contact_data`. El comando informa modelo, clave interna y campo, nunca el valor, y no modifica registros.

## Evidencia

- Reproducción previa: perfil y privacidad aceptaban texto alfabético; el lead rechazaba letras y `5 usd`.
- Regresión nueva: 10 pruebas aprobadas.
- Regresión de cuentas, clientes, leads, privacidad y portal: 201 aprobadas, 5 omitidas clasificadas.
- Django check, Ruff y compilación: aprobados.
