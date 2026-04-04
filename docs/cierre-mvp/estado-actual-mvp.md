# Estado actual del MVP — Packing Exportación

**Fecha:** 2026-04-04
**Rama:** `main`

---

## Resumen ejecutivo

El MVP está **operativo**. El flujo completo (Recepción → Desverdizado → Ingreso Packing → Proceso → Control → Paletizado → Cámaras) está implementado y funcional en ambos backends (SQLite y Dataverse), con un gap bloqueante pendiente que impide declarar el cierre formal.

---

## Qué está cerrado y operativo

| Componente | SQLite | Dataverse |
|---|---|---|
| Recepción de bins (flujo lote abierto) | Funcional | Funcional |
| Pesaje / conformación de lote (en cierre de Recepción) | Funcional | Funcional |
| Dashboard con KPIs | Funcional | Funcional (lotes cerrados = 0; limitación aceptada) |
| Cámara de mantención | Funcional | Funcional |
| Desverdizado | Funcional | Funcional |
| Calidad desverdizado | Funcional | Funcional |
| Ingreso a packing | Funcional | Funcional |
| Registro packing | Funcional | Funcional |
| Control proceso packing | Funcional | Funcional |
| Calidad pallet | Funcional | Funcional |
| Calidad pallet — muestras | Funcional | Funcional (tabla creada 2026-04-04) |
| Cámara de frío | Funcional | Funcional |
| Medición temperatura salida | Funcional | Funcional |
| Consulta jefatura (lista lotes) | Funcional | Funcional |
| Exportación CSV | Funcional | Funcional |
| Consulta jefatura (filtro productor) | Funcional | **Pendiente** (ver límites) |
| Trazabilidad de eventos (RegistroEtapa) | Funcional | No-op con log local (aceptado) |

---

## Rutas web activas (`/operaciones/`)

| Ruta | Vista |
|------|-------|
| `/operaciones/` | Dashboard |
| `/operaciones/recepcion/` | Recepción de bins y cierre de lote (incluye pesaje) |
| `/operaciones/desverdizado/` | Ingreso/salida de desverdizado |
| `/operaciones/ingreso-packing/` | Ingreso a proceso de packing |
| `/operaciones/proceso/` | Proceso de packing |
| `/operaciones/control/` | Control de calidad |
| `/operaciones/paletizado/` | Paletizado |
| `/operaciones/camaras/` | Cámaras de frío y mantención |
| `/operaciones/consulta/` | Consulta de jefatura |
| `/operaciones/consulta/exportar/` | Exportación CSV de lotes |

> **Nota:** No existe `/operaciones/pesaje/` como ruta independiente. El pesaje del lote (kg bruto/neto) se captura en el formulario de cierre del lote dentro de Recepción.

---

## Backends disponibles

| Backend | Variable | Uso |
|---------|----------|-----|
| SQLite | `PERSISTENCE_BACKEND=sqlite` | Desarrollo local, tests |
| Dataverse | `PERSISTENCE_BACKEND=dataverse` | Producción / entorno real |

---

## Tests

- **196 tests**, todos pasan en SQLite.
- Los tests corren siempre contra SQLite. Para validación contra Dataverse real, usar scripts en `scripts/dataverse/`.

---

## Gaps pendientes

Ver tabla completa en [`limites-aceptados-mvp.md`](./limites-aceptados-mvp.md).

| Brecha | Bloquea cierre |
|--------|:--------------:|
| `filtro_productor` en consulta jefatura (Dataverse) | **Sí** |
| `estado` del lote no persiste en Dataverse | No |
| `RegistroEtapa` no-op en Dataverse | No |
| `SequenceCounter` no atómico en Dataverse | No |
| ACID transactions no disponibles | No |

---

## Deuda técnica narrativa

Los PR #43 y #44 cerraron el flujo Dataverse completo e integraron `crf21_etapa_actual` como fuente de verdad del avance operativo del lote. La única deuda que bloquea el cierre formal es el filtro por productor en la consulta jefatura, cuya solución requiere agregar `codigo_productor` al nivel del lote en Dataverse (campo disponible actualmente solo en `crf21_bins`).

---

## Referencias

- `python-app/TECHNICAL_CHANGES.md` — Historial técnico detallado por iteración
- `DATAVERSE_GUIDE.md` — Integración Dataverse, tablas activas, límites §17
- `docs/cierre-mvp/limites-aceptados-mvp.md` — Tabla de gaps con criterio de bloqueo
