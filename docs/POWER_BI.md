# Conexión de Vinova Pro con Power BI

Vinova Pro 2.0.0 ofrece datasets JSON/CSV preparados para BI. Power BI es opcional y no forma parte del runtime de Vinova Pro.

## Requisitos

- Cliente API de solo lectura.
- Alcance `bi:read`.
- Usuario de servicio con `analytics.export` o `data.export`.
- HTTPS válido en producción.
- Token guardado como parámetro secreto, no dentro de la URL.

## Endpoint recomendado

```text
https://vinova.example.com/api/v1/bi/sales/?limit=5000
```

Datasets disponibles: `sales`, `invoices`, `inventory`, `customers`, `leads` y `vehicles`.

## Ejemplo Power Query

Cree parámetros `VinovaBaseUrl` y `VinovaToken`. Marque el token como sensible cuando la herramienta lo permita.

```powerquery
let
    Endpoint = VinovaBaseUrl & "/api/v1/bi/sales/?limit=5000",
    Source = Json.Document(
        Web.Contents(
            Endpoint,
            [Headers = [Authorization = "Bearer " & VinovaToken]]
        )
    ),
    Rows = Source[results],
    Result = if List.Count(Rows) = 0 then #table({}, {}) else Table.FromRecords(Rows)
in
    Result
```

## Actualización incremental

Use:

```text
updated_since=2026-07-01T00:00:00-05:00
limit=5000
offset=0
```

Para volúmenes mayores, incremente `offset` hasta que `count` sea cero. Mantenga la fecha de última carga confirmada y no la avance si una página falla.

## Sucursal

Una credencial ligada a sucursal siempre queda limitada a esa sucursal. Una credencial global puede enviar `branch=<id>`. Cree credenciales diferentes cuando cada área deba tener un alcance separado.

## Protección de datos

Los datasets `customers` y `leads` excluyen nombres, documentos, correos, teléfonos, WhatsApp, mensajes y notas internas. No use la exportación contable como fuente general de BI porque puede contener datos tributarios sensibles.

## Diagnóstico

- `401`: token inválido, revocado, vencido o IP no autorizada.
- `403`: falta alcance o permiso del usuario de servicio.
- `429`: se alcanzó el rate limit del cliente.
- `400`: filtro o formato inválido.

Revise `/dashboard/integrations/` y los logs de integración sin copiar el token en tickets o capturas.
