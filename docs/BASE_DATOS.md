# Base de datos e integridad

## Motores

PostgreSQL 16 es el motor objetivo de operación y concurrencia. SQLite se usa
solo para pruebas locales rápidas; no demuestra locks ni carreras equivalentes.

## Modelo

La auditoría inventarió 85 modelos propios y 57 migraciones numeradas. La
instalación es monocompañía; `Branch` expresa alcance operativo, no tenant.

```text
Company → Branch
User → UserRole → Role → PermissionCode
User ↔ Customer.account
Customer ↔ CustomerVehicle ↔ Vehicle
Lead → Customer → SaleRecord → InvoiceRecord/PrivateDocument
InventoryItem → BranchStock → StockMovement
Customer/Vehicle → ServiceOrder
```

## Integridad

- las migraciones son la fuente del esquema y no se reescriben;
- servicios críticos usan `transaction.atomic`, `select_for_update`, locks
  advisory o idempotencia según el dominio;
- constraints/estados complementan, pero no sustituyen, autorización;
- querysets se filtran por sucursal u ownership antes de resolver objetos;
- secuencias, saldos, stock y vínculos se modifican mediante servicios;
- auditoría y archivos tienen lifecycle/compensación ante rollback.

## Operación de esquema

```bash
python manage.py showmigrations
python manage.py makemigrations --check --dry-run
python manage.py migrate --plan
python manage.py migrate
```

`migrate` exige backup previo en un entorno real. Las carreras PostgreSQL y el
plan limpio se revalidan en B12; los resultados históricos no sustituyen ese
gate.

Consulte [Backups](BACKUPS.md), [Transfer](TRANSFER.md) y
[Recuperación](EMERGENCY_RECOVERY.md).
