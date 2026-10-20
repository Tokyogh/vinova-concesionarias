# F13 — Documentación bilingüe integral del código

Fecha de evidencia local: 2026-10-16

## Criterio

La documentación interna usa español primero e inglés después. Se preservan shebangs, imports futuros, `DOCTYPE`, sintaxis de Django, parsers y comportamiento. Se excluyen dependencias, `static/vendor/`, `web_carros/`, migraciones históricas, binarios, JSON estricto y generados.

Los nombres descriptivos de tests siguen funcionando como especificación ejecutable; no se insertan docstrings en cada caso de prueba. Sí se exige cabecera bilingüe en el módulo. Para código productivo se exige además docstring bilingüe en clases o funciones de alta complejidad: 60 líneas o más, o al menos 10 nodos de decisión/control.

## Bloque 1 — Python e interfaz

La herramienta reproducible `scripts/audit_bilingual_documentation.py` inventaría archivos versionados, aplica exclusiones explícitas y puede normalizar solo comentarios/docstrings. Resultado del primer bloque:

| Superficie | Cobertura |
|---|---:|
| módulos Python propios elegibles | 575/575 con ES y EN |
| símbolos productivos complejos | 148/148 con docstring |
| templates propios | 211/211 con ES y EN |
| CSS propio | 53/53 con ES y EN |
| JavaScript propio | 7/7 con ES y EN |

Se conservaron los encabezados anteriores como contexto cuando aportaban detalle. Los docstrings complejos identifican responsabilidad y, cuando el código lo demuestra, transacción/locking, autorización, auditoría y rechazo de estados inválidos.

## Bloque 2 — operación y cobertura interna

Se incorporaron encabezados bilingües compatibles con parser en 61/61 archivos propios de Docker, Compose, Nginx, shell, PowerShell, CMD/BAT y ejemplos de entorno. Los shebangs permanecen en la primera línea, `param` conserva una posición válida en PowerShell y los ejemplos `.env` declaran explícitamente que no contienen secretos reales.

La auditoría exige además pares ES→EN dentro de los archivos de mayor tamaño, no solo en su cabecera:

| Superficie interna | Criterio | Faltantes |
|---|---:|---:|
| templates/HTML | 80 líneas o más | 0 |
| CSS | 80 líneas o más | 0 |
| JavaScript | 60 líneas o más | 0 |
| operación/configuración | 60 líneas o más | 0 |

Los comentarios internos explican componentes, formularios, navegación, tablas, estados del DOM, reglas visuales, límites operativos y propagación de errores. No sustituyen la autorización, validación ni evidencia ejecutable.

Comando de control:

```powershell
python scripts/audit_bilingual_documentation.py --strict
```

## Verificación del bloque

- auditoría estricta: cero cabeceras o docstrings complejos faltantes;
- AST/`compileall`: válido;
- Ruff: aprobado;
- Django check: cero incidencias;
- 9 regresiones de imports, assets y templates de error aprobadas;
- sintaxis JavaScript válida en 8 archivos versionados;
- sintaxis PowerShell válida en 20 archivos;
- sintaxis Bash válida dentro de una imagen Linux aislada;
- cinco composiciones Docker válidas: local, producción, staging, QA y QA CLI;
- `check_release_readiness --strict`: 9 controles aprobados;
- `diff --check`: limpio.

La comprobación ejecutable específica de plantillas Nginx no se repitió desde el host porque no dispone de binarios locales `nginx`/`openssl`. El control estático de release sí aprobó Docker/Nginx y las plantillas solo recibieron comentarios; F16 debe repetir la validación en el contenedor o runner de release disponible.

## Resultado

F13 queda completada localmente con cobertura reproducible y sin cambios funcionales en archivos de producto. La cobertura cuantitativa no convierte un comentario en evidencia funcional: debe mantenerse junto con cada cambio y se revisará de nuevo en F16.
