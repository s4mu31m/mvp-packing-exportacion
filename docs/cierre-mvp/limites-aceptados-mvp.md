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
| **`filtro_productor` ignorado en consulta jefatura (Dataverse)** | La vista de jefatura no filtra por productor al usar Dataverse | **Pendiente obligatorio.** Requiere persistir `codigo_productor` en `crf21_lote_plantas`, derivado del campo homónimo en `crf21_bins` durante recepción. Implementación pendiente de indexación. | **Sí** |
| `estado` del lote no persiste en Dataverse | Dashboard "lotes cerrados/finalizados" siempre muestra 0 en Dataverse | Aceptado. El avance operativo se representa mediante `etapa_actual` (ver DATAVERSE_GUIDE §17). | No |
| `RegistroEtapa` no-op en Dataverse | Sin trazabilidad de eventos en Dataverse; solo log local | Aceptado para esta iteración. `etapa_actual` cubre la trazabilidad mínima operativa. | No |
| `SequenceCounter` no atómico en Dataverse | Posibles correlativos duplicados bajo concurrencia simultánea extrema | Aceptado. Operación secuencial del MVP (un operador activo por flujo). | No |
| Transacciones ACID no disponibles en Dataverse | Sin rollback automático en caso de falla parcial | Aceptado. Limitación conocida de Dataverse Web API. | No |

---

## Notas de diseño

- **No existe brecha por registros históricos sin `etapa_actual`**: el sistema entrará en producción desde cero; todos los registros se crearán bajo la lógica actual.
- **`etapa_actual` como fuente de verdad operativa**: en Dataverse, la progresión del lote se lee desde `crf21_etapa_actual`. En SQLite se deriva con `_etapa_lote()`. Ver `resolve_etapa_lote()` en `infrastructure/dataverse/repositories/__init__.py`.
- **Solución pendiente para `filtro_productor`**: agregar campos `crf21_codigo_productor` (y opcionalmente `crf21_nombre_productor`) a `crf21_lote_plantas`, poblados desde los campos base del lote al momento de recepción. Con eso, la consulta jefatura podrá filtrar directamente sobre la entidad lote sin N+1 llamadas a bins.

---

## Referencias

- `DATAVERSE_GUIDE.md` — Sección 17: Límites aceptados del MVP
- `python-app/TECHNICAL_CHANGES.md` — Sección "Limitaciones remanentes" (iteración 2026-03-31 b)
- `docs/cierre-mvp/estado-actual-mvp.md` — Estado ejecutivo del MVP
