# TC-002 — Cierre CalidadPalletMuestra, horas_desverdizado y UX operativa

**Fecha:** 2026-03-30
**Rama:** `main`
**Commit de referencia:** `7e44bd0` (Add CalidadPalletMuestra model and UI/UX updates)
**Tipo de cambio:** Cierre / Consolidacion de features parciales

---

## Contexto

El commit `7e44bd0` introdujo:
- Modelo `CalidadPalletMuestra` + migracion
- Formulario `CalidadPalletMuestraForm`
- Campo `horas_desverdizado` en modelo `Desverdizado`
- Refactorizacion de templates operativos a layout `op-layout` con selectores y paneles de contexto
- Smoke tests basicos

Sin embargo, varias piezas quedaron a medio conectar:
- `CalidadPalletMuestra` existia como modelo y form pero sin integracion en vista, template ni tests
- `horas_desverdizado` no tenia validacion server-side en el formulario
- Templates operativos tenian JS duplicado y el panel de contexto de `camaras.html` estaba incompleto
- La migracion 0009 no incluia el campo `source_event_id` de `AuditSourceModel`
- Los smoke tests de consulta jefatura fallaban tras la introduccion de roles (commit `8fbb4c5`)

Este cambio cierra todos esos cabos sueltos.

---

## Archivos creados

### `python-app/src/operaciones/templates/operaciones/includes/op_common_js.html`

Include compartido con la inicializacion de fecha/hora y la funcion `fmt()`, antes duplicada en 7 templates.

### `python-app/src/operaciones/migrations/0010_fix_calidad_pallet_muestra_source_event_id.py`

Migracion correctiva: agrega `source_event_id` a `CalidadPalletMuestra` (faltaba en 0009).

### `docs/technical-changes/TC-002-cierre-calidad-muestra-desverdizado-ux.md`

Este documento.

---

## Archivos modificados

### `python-app/src/operaciones/views.py`

- Importa `CalidadPalletMuestraForm` y `CalidadPalletMuestra`
- `PaletizadoView.get_context_data()` ahora incluye `form_muestra` en el contexto
- Nuevo metodo `PaletizadoView._save_muestras()`: parsea los campos `muestra_N_*` del POST y persiste via ORM directo (SQLite-only, documentado con TODO Dataverse)
- `PaletizadoView.post()` (action=calidad): tras guardar `CalidadPallet` (cabecera), llama `_save_muestras()` para guardar hasta 3 muestras individuales

### `python-app/src/operaciones/forms.py`

- `DesverdizadoForm`: help_text de `horas_desverdizado` actualizado para documentar que reemplaza el campo legacy `proceso`
- `DesverdizadoForm.clean_horas_desverdizado()`: validacion server-side del rango 1-240

### `python-app/src/operaciones/models.py`

- `CalidadPalletMuestra`: docstring actualizado documentando que la persistencia es solo SQLite por ahora

### `python-app/src/operaciones/templates/operaciones/paletizado.html`

- Seccion "Muestras individuales" agregada dentro del tab de calidad: boton para agregar hasta 3 muestras con campos temperatura, peso, n_frutos, aprobada, observaciones
- JS: funciones `addMuestra()` y `removeMuestra()` para gestion dinamica de filas
- JS comun extraido a include compartido

### `python-app/src/operaciones/templates/operaciones/camaras.html`

- Panel de contexto: agregados campos Color y Peso total (antes faltaban vs paletizado)
- `poblarContexto()`: actualizado para poblar `ctx-color` y `ctx-peso`
- JS comun extraido a include compartido

### `python-app/src/operaciones/templates/operaciones/proceso.html`

- JS comun extraido a include compartido

### `python-app/src/operaciones/templates/operaciones/control.html`

- JS comun extraido a include compartido

### `python-app/src/operaciones/templates/operaciones/desverdizado.html`

- JS comun extraido a include compartido

### `python-app/src/operaciones/templates/operaciones/ingreso_packing.html`

- JS comun extraido a include compartido

### `python-app/src/operaciones/templates/operaciones/recepcion.html`

- JS comun extraido a include compartido

### `python-app/src/operaciones/templates/operaciones/pesaje.html`

- JS comun extraido a include compartido

### `python-app/src/operaciones/tests.py`

- Fix: `test_consulta_jefatura` y `test_consulta_jefatura_con_filtros` ahora usan usuario con `is_staff=True`
- Nuevo: `test_consulta_jefatura_redirect_sin_rol` — verifica que operador sin rol es redirigido
- Nuevo: `HorasDesverdizadoModelTest.test_horas_null_por_defecto` — horas es None por defecto
- Nuevo: `HorasDesverdizadoModelTest.test_proceso_legacy_no_interfiere` — los campos son independientes
- Nuevo: `DesverdizadoFormValidationTest` (7 tests) — validacion server-side de rango 0/1/240/241/negativo/vacio
- Nuevo: `CalidadPalletMuestraModelTest` (4 tests) — CRUD, multiples por pallet, opcionales, ordering
- Nuevo: `PaletizadoViewTest` (2 tests) — form_muestra en contexto, campos en pallets_data_json
- Nuevo: `CamarasViewTest` (2 tests) — color y peso en pallets_data_json

---

## Decisiones tomadas

| Decision | Razon |
|----------|-------|
| CalidadPalletMuestra via ORM directo, sin use case/repositorio | El modelo es local-only. Crear repositorio Dataverse sin tabla destino seria incoherente. Se documenta con TODO. |
| Maximo 3 muestras por sesion | Alineado con practica operativa (2-3 muestras por pallet). No es limite de BD, solo de UI. |
| Validacion horas 1-240 server-side | El form ya tenia min/max en HTML attrs (client-only). Server-side cierra la brecha. |
| JS comun extraido a include, no a archivo estatico | El include contiene un template tag (`fmt()` usa caracter Unicode), y el patron de include es consistente con el resto del proyecto. |
| Fix migracion 0009 en nueva migracion 0010 | No se modifica migraciones ya aplicadas. Migracion aditiva es la forma correcta. |

---

## Compatibilidad SQLite / Dataverse

| Entidad | SQLite | Dataverse |
|---------|--------|-----------|
| CalidadPalletMuestra | Funcional (ORM directo) | No soportado. Sin tabla ni repositorio. TODO documentado. |
| CalidadPallet (cabecera) | Funcional (via repositorio) | Stub (NotImplementedError) |
| Desverdizado.horas_desverdizado | Funcional | Stub (campo se pasa en extra, se guarda si la tabla lo tiene) |
| Templates / JS | N/A | N/A |

El backend switch (`PERSISTENCE_BACKEND`) no se ve afectado. `CalidadPalletMuestra` se guarda fuera del repository layer, directamente via ORM. Si se cambia a Dataverse, la cabecera (`CalidadPallet`) fallaria con `NotImplementedError` antes de llegar a las muestras.

---

## Pruebas agregadas

- 152 tests pasan (vs ~134 antes)
- 18 tests nuevos/corregidos
- Cobertura funcional: validacion de formulario, persistencia de modelo, contexto de vista, acceso por rol

---

## Pendientes derivados reales

1. **Repositorio Dataverse para CalidadPalletMuestra** — cuando se defina la tabla `crf21_calidad_pallet_muestras` en Dataverse, crear repositorio y use case dedicado
2. **Repositorio Dataverse para CalidadPallet (cabecera)** — actualmente stub con `NotImplementedError`
3. **Campo `temporada` en hidden inputs** — los templates lo envian siempre vacio; funciona porque `_temporada(request)` cae al fallback de sesion/ano, pero seria mas limpio poblarlo via JS
4. **Admin interface** — `admin.py` esta vacio; no hay forma de inspeccionar registros via Django admin (no es blocker para MVP)
