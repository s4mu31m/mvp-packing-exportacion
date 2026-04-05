# Límites aceptados del MVP — Packing Exportación

**Fecha de revisión:** 2026-04-04
**Fuente:** DATAVERSE_GUIDE.md §17, TECHNICAL_CHANGES.md, clarificaciones de diseño.

---

## Criterio de cierre

El MVP se considera cerrado cuando todas las brechas marcadas como **Bloquea cierre: Sí** estén resueltas. Las brechas marcadas **No** son compromisos de diseño aceptados, no bugs.

---

## Tabla de límites

| Brecha | Impacto operativo | Decisión | Bloquea cierre |
|--------|-------------------|----------|:--------------:|
| ~~`filtro_productor` ignorado en consulta jefatura (Dataverse)~~ | ~~La vista de jefatura no filtra por productor al usar Dataverse~~ | **Resuelto 2026-04-04.** Campo `crf21_codigo_productor` agregado a `crf21_lote_plantas` (opcional, texto). Se puebla al cerrar el lote desde el primer bin. Filtro activo en `_lotes_enriquecidos_dataverse()`. | ~~Sí~~ → **No** |
| `estado` del lote no persiste en Dataverse | Dashboard "lotes cerrados/finalizados" siempre muestra 0 en Dataverse | Aceptado. El avance operativo se representa mediante `etapa_actual` (ver DATAVERSE_GUIDE §17). | No |
| `RegistroEtapa` no-op en Dataverse | Sin trazabilidad de eventos en Dataverse; solo log local | Aceptado para esta iteración. `etapa_actual` cubre la trazabilidad mínima operativa. | No |
| `SequenceCounter` no atómico en Dataverse | Posibles correlativos duplicados bajo concurrencia simultánea extrema | Aceptado. Operación secuencial del MVP (un operador activo por flujo). | No |
| Transacciones ACID no disponibles en Dataverse | Sin rollback automático en caso de falla parcial | Aceptado. Limitación conocida de Dataverse Web API. | No |

---

## Notas de diseño

- **No existe brecha por registros históricos sin `etapa_actual`**: el sistema entrará en producción desde cero; todos los registros se crearán bajo la lógica actual.
- **`etapa_actual` como fuente de verdad operativa**: en Dataverse, la progresión del lote se lee desde `crf21_etapa_actual`. En SQLite se deriva con `_etapa_lote()`. Ver `resolve_etapa_lote()` en `infrastructure/dataverse/repositories/__init__.py`.
- **`filtro_productor` resuelto (2026-04-04)**: campo `crf21_codigo_productor` agregado a `crf21_lote_plantas` como columna opcional de texto en Power Apps. Se puebla automáticamente al cerrar el lote (`cerrar_lote_recepcion`) desde el primer bin del lote. La consulta jefatura filtra directamente sobre el campo del lote sin N+1 llamadas a bins.

---

## Referencias

- `DATAVERSE_GUIDE.md` — Sección 17: Límites aceptados del MVP
- `python-app/TECHNICAL_CHANGES.md` — Sección "Limitaciones remanentes" (iteración 2026-03-31 b)
- `docs/cierre-mvp/estado-actual-mvp.md` — Estado ejecutivo del MVP
