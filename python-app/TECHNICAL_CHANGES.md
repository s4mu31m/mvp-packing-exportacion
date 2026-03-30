# Cambios Técnicos — Iteración 2026-03-30: Flujo Operativo con Contexto de Lote

**Branch:** `main`
**Fecha:** 2026-03-30

---

## Resumen iteración 2026-03-30

Avance funcional sobre el flujo operativo: recepción con lote abierto y campos base bloqueados,
selectores de lote en desverdizado e ingreso packing, consulta jefatura con datos reales,
dashboard con KPIs reales, y DesverdizadoForm refactorizado.

### Archivos modificados
- `python-app/src/operaciones/forms.py`
- `python-app/src/operaciones/views.py`
- `python-app/src/operaciones/templates/operaciones/recepcion.html`
- `python-app/src/operaciones/templates/operaciones/desverdizado.html`
- `python-app/src/operaciones/templates/operaciones/ingreso_packing.html`
- `python-app/src/operaciones/templates/operaciones/dashboard.html`
- `python-app/src/operaciones/templates/operaciones/consulta.html`

### Cambios funcionales
1. **Recepcion** — nuevo flujo de 3 acciones: `iniciar`, `agregar_bin`, `cerrar`.
   El `lote_code` se almacena en sesión. Tras el primer bin, los campos base del lote
   (codigo_productor, tipo_cultivo, variedad_fruta, color, fecha_cosecha) se bloquean
   como readonly. El backend valida incompatibilidades entre bins del mismo lote.
2. **BinForm** — añadidos `tipo_cultivo`, `numero_cuartel`, `color` (necesarios para
   generación del bin_code y para campos base del lote).
3. **IniciarLoteForm** / **CerrarLoteForm** — nuevos formularios para el flujo de lote abierto.
4. **DesverdizadoForm** — `proceso` renombrado a `color` + `horas_desverdizado`. El campo
   `color` mapea a `color_salida` en el modelo; `horas_desverdizado` se persiste en `proceso`
   como texto (pendiente: agregar columna `horas_desverdizado` al modelo Desverdizado).
5. **DesverdizadoView** — muestra selector de lotes cerrados pendientes; auto-selección de
   tab mantencion/desverdizado según disponibilidad_camara del lote.
6. **IngresoPackingView** — muestra selector de lotes pendientes; `via_desverdizado` se
   auto-detecta desde el historial del lote.
7. **ConsultaJefaturaView** — datos reales con etapa derivada, filtros por productor y estado.
8. **DashboardView** — KPIs reales desde DB (lotes abiertos/cerrados, bins hoy, total lotes).

### Decisiones técnicas
- Los campos base del lote se guardan en `request.session["lote_activo_campos_base"]`.
- La función `_etapa_lote()` determina la etapa actual revisando existencia de registros asociados.
- Los selectores de lote en desverdizado e ingreso packing usan ORM directo en la vista
  (consultas de lectura, no pasan por repositorios). Compatible con SQLite y Dataverse.

### Brechas pendientes
- `horas_desverdizado`: agregar campo al modelo `Desverdizado` en próxima migración.
- Etapas proceso/control/paletizado/camaras: reciben `lote_pendientes` en contexto pero
  aún piden `lote_code` manual (pendiente mismo patrón de selector).
- Calidad de cítricos: múltiples muestras por pallet no implementadas aún.
- Tests de vistas: no existen tests de integración para las vistas web.

---

## Iteración 2026-03-30 (patch): Fecha/hora en tiempo real y via_desverdizado oculto

### Archivos modificados
- `python-app/src/operaciones/templates/operaciones/control.html`
- `python-app/src/operaciones/templates/operaciones/pesaje.html`
- `python-app/src/operaciones/templates/operaciones/ingreso_packing.html`

### Cambios funcionales

1. **Fecha y hora en tiempo real — todas las vistas**
   Se añadió el snippet JS de auto-fill a las dos vistas que faltaban (`control.html` y `pesaje.html`).
   Todas las vistas operacionales tienen ahora el comportamiento uniforme:
   - `input[type="date"]` → pre-poblado con la fecha local del dispositivo al cargar la página.
   - `input.campo-hora` → pre-poblado con la hora local (HH:MM) al cargar la página.
   El valor solo se aplica si el campo está vacío; el usuario puede modificarlo libremente.
   Vistas cubiertas: `recepcion`, `desverdizado`, `ingreso_packing`, `proceso`, `control`, `pesaje`, `paletizado`, `camaras`.

2. **`via_desverdizado` oculto en Ingreso Packing**
   El campo `via_desverdizado` dejó de ser un control visible en el formulario de ingreso a packing.
   - Se mueve al **panel de contexto del lote** como dato informativo ("Via desv.: Sí / No").
   - Se envía automáticamente al backend mediante un `<input type="hidden" name="via_desverdizado">`.
   - El valor se establece por JS al seleccionar el lote: `"on"` si `LOTES_DATA[code].via_desverdizado === true`, `""` si `false` (Django BooleanField interpreta ausencia de valor como `False`).
   - El operador no puede modificarlo; queda determinado por el historial del lote (existencia de registro de desverdizado).

---

# Cambios Técnicos — Generación Dinámica de Códigos, Flujo de Recepción con Lote Abierto y Adaptación al Schema Real de Dataverse

**Branch:** `feature/mvp-dataverse-backend-switch`
**Fecha:** 2026-03-29
**Migración aplicada:** `0007_lote_estado_temporada_sequence_pallet_lote_unique`

---

## Resumen

Este documento describe los cambios técnicos realizados para alinear el MVP con el flujo operativo real acordado con el cliente:

1. Los códigos de Bin, LotePlanta y Pallet se generan automáticamente en backend. El usuario no los ingresa.
2. El LotePlanta se crea al **iniciar** la recepción y permanece abierto mientras se agregan bins.
3. El correlativo de LotePlanta es **por temporada**, no reinicia por día.
4. Un lote no puede pertenecer a más de un pallet (restricción en base de datos).
5. El estado del lote se gestiona explícitamente: `abierto → cerrado → finalizado/anulado`.
6. El backend se adapta al schema **real** de Dataverse (prefijo `crf21_`, validado el 2026-03-29).

---

## 1. Cambios en el modelo de datos

### 1.1 Nuevo enum `LotePlantaEstado`

```python
class LotePlantaEstado(models.TextChoices):
    ABIERTO    = "abierto"
    EN_PROCESO = "en_proceso"
    CERRADO    = "cerrado"
    FINALIZADO = "finalizado"
    ANULADO    = "anulado"
```

### 1.2 Nuevos campos en `Lote`

| Campo | Tipo | Default | Descripción |
|---|---|---|---|
| `estado` | CharField (choices) | `abierto` | Estado del ciclo de vida del lote |
| `temporada_codigo` | CharField | `""` | Código explícito de temporada. Ej: `2025-2026` |
| `correlativo_temporada` | PositiveIntegerField | null | Correlativo ascendente dentro de la temporada |

### 1.3 Nuevo modelo `SequenceCounter`

Tabla de correlativos para generación dinámica de códigos (solo SQLite). El backend Dataverse determina el correlativo contando registros existentes.

```
operaciones_sequence_counter
  entity_name  VARCHAR(50)  — 'lote', 'bin', 'pallet'
  dimension    VARCHAR(50)  — temporada_codigo (lote) o YYYYMMDD (pallet) o combinacion de campos (bin)
  last_value   INT          — último valor asignado
  updated_at   DATETIME
  UNIQUE (entity_name, dimension)
```

El acceso es atómico vía `SELECT FOR UPDATE` para garantizar unicidad en concurrencia (SQLite).

### 1.4 Unicidad de lote en `PalletLote`

Se agregó la restricción `uq_pallet_lote_lote_unico` sobre el campo `lote` de la tabla `operaciones_pallet_lote`. Garantiza a nivel de base de datos que un lote no puede estar en más de un pallet.

---

## 2. Nuevos servicios

### `operaciones/services/season.py`

```python
resolve_temporada_codigo(fecha_operativa=None) → str
```

Resuelve el código de temporada desde la fecha. Regla: mes ≥ 10 → `{año}-{año+1}`, mes < 10 → `{año-1}-{año}`.

Ejemplos:
- `2025-10-01` → `"2025-2026"`
- `2026-01-15` → `"2025-2026"`
- `2026-10-01` → `"2026-2027"`

### `operaciones/services/sequences.py`

```python
get_next_sequence(entity_name: str, dimension: str) → int
```

Obtiene el siguiente correlativo para la entidad y dimensión dadas. Operación atómica bajo transacción Django (SQLite). En Dataverse el correlativo se determina contando registros existentes.

### `operaciones/services/code_generators.py`

| Función | Formato generado | Ejemplo |
|---|---|---|
| `build_bin_code(codigo_productor, tipo_cultivo, variedad_fruta, numero_cuartel, fecha_cosecha)` | `{cod_prod}-{cultivo}-{variedad}-{cuartel}-{DDMMYY}-{NNN}` | `AG01-LM-Eur-C05-290326-001` |
| `build_lote_code(temporada_codigo, correlativo)` | `LP-TTTT-TTTT-NNNNNN` | `LP-2025-2026-000001` |
| `build_pallet_code(fecha)` | `PA-YYYYMMDD-NNNN` | `PA-20260329-0012` |
| `next_lote_correlativo(temporada_codigo)` | devuelve `(lote_code, correlativo)` | — |

**Formato `bin_code`** — sigue la hoja "Código de barra" del Excel del cliente:
- `{codigo_productor}`: código de la empresa productora (ej: `AG01`)
- `{tipo_cultivo}`: abreviatura del cultivo (ej: `LM`)
- `{variedad_fruta}`: nombre de variedad (ej: `Eur`)
- `{numero_cuartel}`: identificador del cuartel (ej: `C05`)
- `{DDMMYY}`: fecha de cosecha en formato día-mes-año abreviado (ej: `290326`)
- `{NNN}`: correlativo diario de 3 dígitos, independiente por combinación de los 5 campos anteriores

---

## 3. Nuevos casos de uso

### `iniciar_lote_recepcion(payload)`

Crea un lote planta en estado `abierto` al iniciar una sesión de recepción. El `lote_code` y `correlativo_temporada` se generan automáticamente.

**Payload requerido:** `temporada`
**Payload opcional:** `temporada_codigo`, `operator_code`, `fecha_conformacion`

**Resultado:**
```json
{
  "lote_id": 1,
  "lote_code": "LP-2025-2026-000001",
  "temporada_codigo": "2025-2026",
  "correlativo_temporada": 1,
  "estado": "abierto"
}
```

### `agregar_bin_a_lote_abierto(payload)`

Registra un bin (generando su `bin_code`) y lo asocia inmediatamente al lote abierto indicado.

**Validaciones:**
- El lote debe existir y estar en estado `abierto`.
- El bin no puede estar ya asignado a otro lote.

**Payload requerido:** `temporada`, `lote_code`
**Payload opcional:** `fecha_cosecha`, `codigo_productor`, `tipo_cultivo`, `variedad_fruta`, `numero_cuartel`, `kilos_bruto_ingreso`, etc.

**Resultado:**
```json
{
  "bin_id": 5,
  "bin_code": "AG01-LM-Eur-C05-290326-001",
  "lote_id": 1,
  "lote_code": "LP-2025-2026-000001",
  "bin_lote_id": 3
}
```

### `cerrar_lote_recepcion(payload)`

Cierra el lote: cambia estado de `abierto` a `cerrado`. Después del cierre no se pueden agregar bins.

**Validaciones:**
- El lote debe estar en estado `abierto`.
- El lote debe tener al menos un bin asociado.

**Payload requerido:** `temporada`, `lote_code`

---

## 4. Cambios en casos de uso existentes

### `registrar_bin_recibido`

- `bin_code` ya **no es requerido** en el payload. Si no se provee, se genera automáticamente via `build_bin_code()` con los 5 campos base del `extra`.
- Si se provee explícitamente, se respeta (compatibilidad con integraciones upstream).

### `crear_lote_recepcion`

- `lote_code` ya **no es requerido** en el payload. Si no se provee, se genera con correlativo por temporada.
- `bin_codes` sigue siendo requerido (lista de bins a asociar).
- El lote se crea directamente en estado `cerrado` al usar este caso de uso (flujo legacy).

### `cerrar_pallet`

- `pallet_code` ya **no es requerido** en el payload. Si no se provee, se genera via `build_pallet_code()`.
- `lote_codes` sigue siendo requerido.

---

## 5. Cambios en formularios y vistas

### `BinForm`

Eliminado el campo `bin_code`. El usuario ya no ingresa el código del bin.

### `LoteForm`

Eliminado el campo `lote_code`. El usuario ya no ingresa el código del lote.

### `RecepcionView`

El payload ya no incluye `bin_code`.

### `PesajeView`

El payload ya no incluye `lote_code`.

---

## 6. Flujo de recepción — antes y después

### Antes (flujo legacy — aún disponible)

```
1. Operador ingresa bins sueltos uno a uno (con bin_code manual)
2. Operador conforma lote ingresando lote_code manual y listado de bin_codes
```

### Después (nuevo flujo preferido)

```
1. Iniciar recepción → lote_code generado automáticamente (estado: abierto)
2. Capturar atributos del bin → bin_code generado automáticamente
3. Bin queda asociado al lote abierto en la misma operación
4. Repetir paso 2-3 por cada bin
5. Cerrar lote → estado cambia a "cerrado"
```

---

## 7. Reglas de negocio enforced

| Regla | Mecanismo |
|---|---|
| bin_code único por temporada | UniqueConstraint en DB |
| lote_code único por temporada | UniqueConstraint en DB |
| pallet_code único por temporada | UniqueConstraint en DB |
| Un bin en un solo lote | Validación en use case + BinLote unique constraint |
| Un lote en un solo pallet | UniqueConstraint `uq_pallet_lote_lote_unico` en DB |
| Correlativo de lote no se reutiliza | SequenceCounter nunca decrementa |
| No agregar bins a lote cerrado | Validación de estado en `agregar_bin_a_lote_abierto` |
| Cerrar lote requiere mínimo un bin | Validación en `cerrar_lote_recepcion` |

---

## 8. Adaptación al schema real de Dataverse

### 8.1 Validación del schema (2026-03-29)

El schema real de Dataverse fue validado via `GET /api/dataverse/check_tables/`. Las 14 tablas responden correctamente con sus registros de muestra. El publisher usa el prefijo **`crf21_`** (no `CaliPro_` como se supuso antes de la validación).

### 8.2 Corrección del mapping (`infrastructure/dataverse/mapping.py`)

El archivo fue reescrito completamente para reflejar los nombres reales:

| Concepto | Antes (supuesto) | Después (real) |
|---|---|---|
| Entidades | `CaliPro_bins`, `CaliPro_loteplantas` | `crf21_bins`, `crf21_lote_plantas` |
| Campos | `CaliPro_bincode`, `CaliPro_codigoproductor` | `crf21_bin_code`, `crf21_codigo_productor` |
| Junction bins-lotes | `CaliPro_binloteplantas` | `crf21_bin_lote_plantas` |
| Junction pallets-lotes | `CaliPro_palletloteplantas` | `crf21_lote_planta_pallets` |

### 8.3 Campos del dominio sin equivalente en Dataverse

Los siguientes campos existen en el dominio Django pero **no tienen columna en Dataverse**. El backend los gestiona localmente o los ignora al persistir:

| Campo dominio | Tabla afectada | Estrategia backend |
|---|---|---|
| `temporada` | bins, lotes, pallets | No se persiste; se filtra por rango de fechas si es necesario |
| `lote_code` | lote_plantas | Se almacena en `crf21_id_lote_planta` |
| `pallet_code` | pallets | Se almacena en `crf21_id_pallet` |
| `estado` | lote_plantas | No existe en Dataverse; `LoteRecord` lo retorna como `"abierto"` por defecto |
| `temporada_codigo` | lote_plantas | No existe en Dataverse; se retorna vacío |
| `correlativo_temporada` | lote_plantas | No existe en Dataverse; se retorna `None` |
| `is_active` | bins, lotes, pallets | Se lee de `statecode == 0` (campo estándar Dataverse) |

### 8.4 `SequenceCounter` sin tabla en Dataverse

No existe tabla de correlativos en Dataverse y el principio del proyecto establece que **Dataverse no se modifica**. Se implementó `DataverseSequenceCounterRepository` que determina el siguiente correlativo **contando registros existentes**:

| Entidad | Estrategia de conteo |
|---|---|
| `bin` | Cuenta bins con `crf21_bin_code` que empiece por el prefijo de dimensión (`cod_prod-cultivo-variedad-cuartel-fecha-`) |
| `lote` | Cuenta lotes con `crf21_fecha_conformacion` en el rango de fechas de la temporada |
| `pallet` | Cuenta pallets con `crf21_fecha` en el día de la dimensión |

> Esta estrategia no es atómica. Race conditions son posibles bajo alta concurrencia. Aceptable para la escala del MVP.

### 8.5 `RegistroEtapa` sin tabla en Dataverse

No existe tabla `registro_etapas` en el schema real de Dataverse. `DataverseRegistroEtapaRepository` es un **no-op** que registra los eventos en el log local (Django `logging`) sin persistirlos en Dataverse. Los casos de uso funcionan sin error porque el registro de eventos es informacional y no bloquea la lógica de negocio.

### 8.6 Tests de conexión Dataverse validados (sección 11 de DATAVERSE_GUIDE.md)

Todos los endpoints de prueba documentados en el guide responden correctamente:

| Endpoint | Resultado |
|---|---|
| `GET /api/dataverse/ping/` | ✅ Conexión exitosa, user/org/BU retornados |
| `GET /api/dataverse/check_tables/` | ✅ 14/14 tablas accesibles con registro de muestra |
| `GET /api/dataverse/get_first_bin_code/` | ✅ `AG01-CE-Santi-C05-280326-01` |
| `POST /api/dataverse/save_first_bin_code/` | ✅ success |

---

## 9. Repositorios Dataverse (`infrastructure/dataverse/repositories/`)

### Estado de implementación

| Repositorio | Estado |
|---|---|
| `DataverseBinRepository` | ✅ Implementado (find_by_code, create con extra, filter_by_codes) |
| `DataverseLoteRepository` | ✅ Implementado (find_by_code, create, filter_by_codes, update) |
| `DataversePalletRepository` | ✅ Implementado (find_by_code, get_or_create) |
| `DataverseBinLoteRepository` | ✅ Implementado (create, find_existing_assignments) |
| `DataversePalletLoteRepository` | ✅ Implementado (get_or_create, find_by_lote) |
| `DataverseRegistroEtapaRepository` | ✅ No-op (sin tabla en Dataverse, log local) |
| `DataverseSequenceCounterRepository` | ✅ Implementado (conteo de registros existentes) |
| `DataverseCamaraMantencionRepository` | 🔲 Stub — pendiente validación de uso real |
| `DataverseDesverdizadoRepository` | 🔲 Stub — pendiente validación de uso real |
| `DataverseCalidadDesverdizadoRepository` | 🔲 Stub — pendiente validación de uso real |
| `DataverseIngresoAPackingRepository` | 🔲 Stub — pendiente validación de uso real |
| `DataverseRegistroPackingRepository` | 🔲 Stub — pendiente validación de uso real |
| `DataverseControlProcesoPackingRepository` | 🔲 Stub — pendiente validación de uso real |
| `DataverseCalidadPalletRepository` | 🔲 Stub — pendiente validación de uso real |
| `DataverseCamaraFrioRepository` | 🔲 Stub — pendiente validación de uso real |
| `DataverseMedicionTemperaturaSalidaRepository` | 🔲 Stub — pendiente validación de uso real |

Los stubs elevan `NotImplementedError` con mensaje descriptivo si son invocados.

---

## 10. Tests

| Suite | Tests | Estado |
|---|---|---|
| `test_sequences_and_codes` | 17 | ✅ Pasan |
| `test_iniciar_lote_recepcion` | 16 | ✅ Pasan |
| Suites existentes | 82 | ✅ Pasan |
| **Total** | **115** | **✅ OK** |

Para correr todos:

```bash
cd python-app/src
python manage.py test operaciones.test
```
