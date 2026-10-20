# R06 — VEHÍCULOS Y GARAJE DIGITAL
**Fase:** R06  
**Estado:** COMPLETADA  
**Fecha:** 2026-10-09  

## Objetivo
Implementar códigos privados de vinculación (VNV-…), canje transaccional, desvinculación con snapshot, transferencia de titularidad (historial preservado), garaje cliente?vehículo, endpoint de canje del cliente, paneles Staff, permisos y migraciones. 

## Cambios principales
- apps/vehicles/models.py: VehicleLinkCode + CustomerVehicle
- apps/customers/models.py: account OneToOne
- Servicios: generate/revoke/redeem (advisory lock + select_for_update), unlink/transfer, link_customer_account
- Vistas/URLs: Staff + cliente vehicles:redeem (/vehiculos/canjear/)
- Migraciones: vehicles.0006, customers.0003 aplicadas en Docker (PostgreSQL)

## Verificaciones (Docker real)
- manage.py check OK
- migrate --plan sin pendientes
- Esquema verificado (avatar/avatar_provider presentes)
- / responde 200 OK
- Tests: apps/vehicles 35/35, apps/customers 32/32, apps/accounts 49/49

## Incidente DB (avatar)
- Migraciones pendientes (accounts.0003/0004, customers.0002/0003, vehicles.0006) aplicadas correctamente al entorno Docker.

F18–F20: IMPLEMENTADO.
