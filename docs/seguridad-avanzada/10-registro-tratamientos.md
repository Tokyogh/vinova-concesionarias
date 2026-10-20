# F10 — Registro preliminar de tratamientos

Fecha técnica: 2026-10-16
Estado: inventario técnico; bases, plazos y contratos pendientes de validación profesional

## Tratamientos observados en código

| Tratamiento | Titulares y datos | Finalidad real | Base candidata, no aprobada | Acceso/destino | Retención técnica |
|---|---|---|---|---|---|
| cuentas y autenticación | usuarios; nombre, correo, teléfono, credenciales hash, sesión, 2FA | acceso y seguridad | contrato, obligación o interés legítimo según relación | personal autorizado; correo para activación | política por definir; sesiones expiran/revocan |
| acceso Staff adaptativo | Staff; hashes de IP, sesión y agente, decisiones | impedir acceso privilegiado riesgoso | seguridad/interés legítimo sujeto a evaluación | aprobadores globales y auditoría | solicitudes y auditoría por definir |
| clientes | clientes; identificación, contacto, dirección, preferencias | relación comercial y expediente | precontrato, contrato, obligación legal | roles autorizados por sucursal | base configurable: 1.825 días y revisión legal |
| prospectos y leads | prospectos; contacto, interés, presupuesto, mensaje, fuente | responder solicitudes y gestionar oportunidades | consentimiento específico u otra base validada | CRM y sucursal pertinente | base configurable: 730 días, luego revisar/anonimizar |
| vehículos y garaje | clientes; vehículos, propiedad/vínculo, historial | venta, servicio y portal propio | contrato/obligación según operación | venta, postventa y titular | ligada a relación y obligaciones documentales |
| ventas, pagos y facturas | clientes; operaciones, importes, comprobantes | ejecutar y acreditar transacciones | contrato y obligaciones legales | roles financieros autorizados | PENDIENTE DE VALIDAR conforme norma aplicable |
| postventa | clientes; vehículo, orden, agenda, responsable y costos | prestar servicio y conservar historial | contrato/obligación | postventa y titular en portal | PENDIENTE DE VALIDAR |
| documentos privados | clientes; archivos, metadatos, hash, estado | soporte contractual y operativo | contrato/obligación | roles autorizados y titular cuando corresponde | base configurable: 2.555 días; revisión legal |
| comunicaciones y campañas | contactos; canal, preferencias, contenido y estado | avisos operativos o marketing | contrato/interés/consentimiento según mensaje | proveedor de correo y roles autorizados | PENDIENTE DE VALIDAR por tipo |
| analítica de catálogo | visitantes; sesión/IP hash, URL, referencia y evento | medir uso comercial | consentimiento opcional implementado | analítica interna | PENDIENTE DE VALIDAR |
| cookies y preferencias | visitantes; versión, fecha y booleanos | recordar elección y opciones | necesidad técnica/consentimiento por categoría | navegador y servidor | 180 días configurables |
| solicitudes de titulares | solicitantes; contacto, referencia parcial, solicitud y verificación | ejercer derechos y demostrar gestión | obligación legal | privacidad y asignado autorizado | PENDIENTE DE VALIDAR |
| auditoría y alertas | usuarios/clientes relacionados; actor, acción, IP, agente, cambios | seguridad, integridad y trazabilidad | obligación/interés legítimo | auditoría/seguridad autorizada | base configurable: 2.555 días y archivo |
| backups y continuidad | copias de datos operativos | recuperación | continuidad/seguridad | operadores de continuidad | base local: 30 días; copia externa pendiente |
| QA y evidencia | testers/usuarios sintéticos; resultados y archivos redactados | demostrar calidad | interés organizacional/contrato | calidad autorizada | 90 días configurados; validar |

## Proveedores y transferencias por despliegue

| Componente configurable | Papel posible | Datos potenciales | Verificación obligatoria |
|---|---|---|---|
| PostgreSQL/hosting | infraestructura o encargado | datos operativos completos | operador, país, acceso, cifrado, contrato, subencargados |
| Redis/Celery | infraestructura temporal | colas, identificadores y cargas de tareas | minimización, expiración, acceso y persistencia |
| correo SMTP | encargado/destinatario según uso | dirección y contenido del mensaje | proveedor, ubicación, TLS, retención y contrato |
| S3/MinIO | encargado de almacenamiento | documentos privados y backups | ubicación, cifrado, borrado, versionado y contrato |
| Cloudinary | encargado de activos públicos | imágenes y metadatos | evitar documentos privados; contrato y ubicación |
| Sentry | encargado de monitoreo | errores y contexto técnico | scrubbing, muestreo, ubicación, contrato y retención |
| MapTiler/unpkg | tercero contactado por navegador | IP y cabeceras técnicas | consentimiento, dominios, contrato y transferencia |
| webhooks/API de terceros | encargado, responsable o destinatario según finalidad | payload configurado | clasificación, minimización, contrato y transferencia |

Ningún proveedor se presume contratado, aprobado o situado en una jurisdicción concreta. La configuración real de staging/producción debe completar este registro y aplicar la normativa SPDP vigente sobre comunicaciones y transferencias.

## Controles de minimización observados

- permisos por rol, sucursal y ownership;
- hashes para señales técnicas de analítica y acceso adaptativo;
- referencia parcial en solicitudes públicas;
- archivos privados separados y descargas autorizadas;
- exportaciones con vencimiento;
- consentimiento opcional apagado por defecto;
- anonimizado controlado con retención legal;
- redacción de secretos en auditoría.

## Brechas de gobierno

- aprobar propietario interno de cada tratamiento;
- convertir bases candidatas en decisiones jurídicas documentadas;
- completar contratos de encargo y matriz de transferencias;
- validar plazos y automatizar revisiones sin borrado ciego;
- decidir necesidad de delegado y evaluaciones de impacto;
- registrar sistemas manuales o externos que no constan en el repositorio.
