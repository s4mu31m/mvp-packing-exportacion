# Testing contra Dataverse — Guía Completa

Guía de referencia para verificar el funcionamiento completo de la app CaliPro
contra el backend Dataverse. Cubre la validación del schema, el aprovisionamiento
de tablas faltantes y la ejecución de los tests E2E.

---

## Prerequisitos

### Variables de entorno requeridas

Todas las operaciones contra Dataverse (management commands y tests) requieren
las siguientes variables:

```bash
PERSISTENCE_BACKEND=dataverse
DATAVERSE_URL=https://tu-org.crm.dynamics.com
DATAVERSE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
DATAVERSE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
DATAVERSE_CLIENT_SECRET=tu-secret-aqui
```

Los tests E2E además requieren:

```bash
CALIPRO_TEST_BACKEND=dataverse
```

> El App Registration en Azure AD debe tener rol **System Customizer** o
> **System Administrator** en el entorno Dataverse para poder crear tablas y campos.

### Ejecutar desde

Todos los comandos se ejecutan desde el directorio `python-app/`.

---

## Orden recomendado en cada deploy

```
Paso 1 → dataverse_ensure_schema --check-only    Detectar gaps de schema
Paso 2 → dataverse_ensure_schema --create        Corregir gaps (si los hay)
Paso 3 → test_schema_validation.py               Confirmar schema completo
Paso 4 → test_dataverse_access.py                Confirmar roles y permisos
Paso 5 → test_dataverse_workflow.py              Confirmar flujos end-to-end
```

Si el paso 3 pasa ✅ y el paso 5 pasa ✅, la app está completamente funcional
contra Dataverse.

---

## Paso 1 — Verificar el schema Dataverse

El comando `dataverse_ensure_schema` audita las 20 tablas (`crf21_*`) requeridas
por la app y reporta qué entidades o campos faltan.

```bash
# Solo verificar (no crea nada, exit 1 si hay gaps)
PERSISTENCE_BACKEND=dataverse python manage.py dataverse_ensure_schema --check-only

# Apuntar a una tabla específica
PERSISTENCE_BACKEND=dataverse python manage.py dataverse_ensure_schema --check-only \
  --table crf21_planilla_desv_calibre
```

**Salida esperada cuando el schema está completo:**

```
------------------------------------------------------------
  OK  crf21_bin
  OK  crf21_lote_planta
  OK  crf21_pallet
  ...
  OK  crf21_planilla_calidad_camara
------------------------------------------------------------
Resultado: 20/20 entidades OK, 0 con gaps.

Schema completo. Sin gaps.
```

**Salida cuando hay gaps:**

```
  MISSING ENTITY  crf21_planilla_desv_calibre
  MISSING FIELDS  crf21_lote_planta (1 campos)
      - crf21_etapa_actual
------------------------------------------------------------
2 gap(s) encontrados. Ejecute con --create para crearlos.
```

---

## Paso 2 — Crear tablas y campos faltantes

### Crear todo de una vez

```bash
PERSISTENCE_BACKEND=dataverse python manage.py dataverse_ensure_schema --create
```

### Crear tabla por tabla (recomendado la primera vez)

Las 4 planillas de control de calidad pueden no existir aún.
Se recomienda crearlas de a una para monitorear el progreso,
ya que la Metadata API de Dataverse puede tardar 30–120 segundos por tabla.

```bash
PERSISTENCE_BACKEND=dataverse python manage.py dataverse_ensure_schema --create \
  --table crf21_planilla_desv_calibre

PERSISTENCE_BACKEND=dataverse python manage.py dataverse_ensure_schema --create \
  --table crf21_planilla_desv_semillas

PERSISTENCE_BACKEND=dataverse python manage.py dataverse_ensure_schema --create \
  --table crf21_planilla_calidad_packing

PERSISTENCE_BACKEND=dataverse python manage.py dataverse_ensure_schema --create \
  --table crf21_planilla_calidad_camara
```

> **Nota:** El comando es idempotente. Si una tabla o campo ya existe, lo omite
> silenciosamente. Es seguro ejecutarlo múltiples veces.

### Re-verificar tras la creación

```bash
PERSISTENCE_BACKEND=dataverse python manage.py dataverse_ensure_schema --check-only
```

### Tablas que crea el comando (las 4 planillas nuevas)

| Tabla Dataverse | Descripción | Campos |
|---|---|---|
| `crf21_planilla_desv_calibres` | Planilla calibres desverdizado | 24 campos |
| `crf21_planilla_desv_semillas` | Planilla semillas desverdizado | 20 campos |
| `crf21_planilla_calidad_packings` | Planilla calidad packing (citricos) | 62 campos |
| `crf21_planilla_calidad_camaras` | Planilla control calidad camaras frio | 33 campos |

---

## Paso 3 — Smoke tests de schema

Validan que las 20 tablas y todos sus campos existan en el entorno Dataverse.
No requieren browser.

```bash
# Suite completa de schema
CALIPRO_TEST_BACKEND=dataverse pytest tests/e2e/test_schema_validation.py -v
```

### Tests individuales

```bash
# Verifica que los 20 entity sets son accesibles via OData
CALIPRO_TEST_BACKEND=dataverse pytest \
  tests/e2e/test_schema_validation.py::test_all_entity_sets_are_accessible -v

# Verifica que los campos criticos existen en cada entidad
CALIPRO_TEST_BACKEND=dataverse pytest \
  tests/e2e/test_schema_validation.py::test_critical_fields_exist_per_entity -v

# Foco en las 4 planillas nuevas (el test mas critico post-deploy)
CALIPRO_TEST_BACKEND=dataverse pytest \
  tests/e2e/test_schema_validation.py::test_new_planilla_tables_are_fully_provisioned -v

# Verifica campos JSON (calibres_grupos, frutas_data, mediciones)
CALIPRO_TEST_BACKEND=dataverse pytest \
  tests/e2e/test_schema_validation.py::test_json_memo_fields_exist -v
```

---

## Paso 4 — Tests de acceso y roles (RBAC)

```bash
CALIPRO_TEST_BACKEND=dataverse pytest tests/e2e/test_dataverse_access.py -v
```

**Cubre:**
- 6 roles operacionales → acceden a su módulo correcto (HTTP 200)
- 6 escenarios de rechazo → HTTP 403 al acceder a módulo ajeno
- Jefatura → accede a `/operaciones/consulta/`
- Otros roles → redirigen a `/usuarios/portal/`
- Control → muestra los 4 links de navegación en el índice

---

## Paso 5 — Tests E2E de workflows

Tests de integración completos contra Dataverse real. Usan browser (Playwright).

### Suite completa

```bash
CALIPRO_TEST_BACKEND=dataverse pytest tests/e2e/test_dataverse_workflow.py -v
```

### Por categoría

```bash
# Flujos operacionales: desverdizado → ingreso packing → proceso → control → paletizado → camaras
CALIPRO_TEST_BACKEND=dataverse pytest tests/e2e/test_dataverse_workflow.py \
  -k "flow" -v

# Validación negativa: formularios rechazan entradas inválidas
CALIPRO_TEST_BACKEND=dataverse pytest tests/e2e/test_dataverse_workflow.py \
  -k "rejects or invalido" -v

# Planillas de control de calidad (desverdizado y packing)
CALIPRO_TEST_BACKEND=dataverse pytest tests/e2e/test_dataverse_workflow.py \
  -k "planilla" -v

# Consulta jefatura y exportación CSV
CALIPRO_TEST_BACKEND=dataverse pytest tests/e2e/test_dataverse_workflow.py \
  -k "consulta or csv" -v
```

### Workflows cubiertos

| Test | Flujo | Qué valida |
|---|---|---|
| `test_dataverse_desverdizado_flow_*` | Desverdizado | Mantencion + desverdizado, etapa, persistencia |
| `test_dataverse_ingreso_packing_flow_*` | Ingreso Packing | Herencia `via_desverdizado`, campos obligatorios |
| `test_dataverse_proceso_flow_*` | Proceso Packing | Linea, calibre, categoria, merma% |
| `test_dataverse_control_proceso_flow_*` | Control Proceso | pH, temperatura, rendimiento% |
| `test_dataverse_paletizado_flow_*` | Paletizado | Calidad + muestras dinámicas |
| `test_dataverse_camaras_flow_*` | Camaras Frio | CamaraFrioRecord, link de control |
| `test_dataverse_control_camaras_planilla_*` | Control Camaras | Planilla JSON mediciones horarias |
| `test_dataverse_consulta_jefatura_*` | Consulta Jefatura | Filtro + CSV con campos heredados |
| `test_dataverse_desverdizado_form_rejects_*` | Validación negativa | Hora inválida, lote requerido |
| `test_dataverse_ingreso_packing_rejects_*` | Validación negativa | kilos_neto > kilos_bruto |
| `test_dataverse_planilla_calibres_*` | Planilla Calibres | JSON `calibres_grupos_json`, defectos |
| `test_dataverse_planilla_semillas_*` | Planilla Semillas | JSON `frutas_data_json`, estadísticas |
| `test_dataverse_planilla_calidad_packing_*` | Planilla Packing | 62 campos defectos, `total_defectos_pct` |
| `test_dataverse_consulta_csv_*` | Exportación CSV | Columnas esperadas + encoding UTF-8 BOM |

---

## Suite completa (todos los pasos juntos)

```bash
CALIPRO_TEST_BACKEND=dataverse pytest \
  tests/e2e/test_schema_validation.py \
  tests/e2e/test_dataverse_access.py \
  tests/e2e/test_dataverse_workflow.py \
  -v --tb=short
```

---

## Ejemplo completo para CI/CD

```bash
#!/usr/bin/env bash
set -euo pipefail

export PERSISTENCE_BACKEND=dataverse
export CALIPRO_TEST_BACKEND=dataverse
export DATAVERSE_URL="https://tu-org.crm.dynamics.com"
export DATAVERSE_TENANT_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
export DATAVERSE_CLIENT_ID="xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx"
export DATAVERSE_CLIENT_SECRET="$SECRET_FROM_CI"

echo "=== [1/4] Verificando schema Dataverse ==="
python manage.py dataverse_ensure_schema --check-only

echo "=== [2/4] Smoke tests de schema ==="
pytest tests/e2e/test_schema_validation.py -v --tb=short

echo "=== [3/4] Tests de acceso y roles ==="
pytest tests/e2e/test_dataverse_access.py -v --tb=short

echo "=== [4/4] Tests E2E de workflows ==="
pytest tests/e2e/test_dataverse_workflow.py -v --tb=short

echo "=== Todos los tests pasaron OK ==="
```

---

## Archivos clave

| Archivo | Descripción |
|---|---|
| `src/infrastructure/dataverse/schema_definition.py` | Fuente de verdad: 20 entidades con todos sus campos |
| `src/core/management/commands/dataverse_ensure_schema.py` | Command para verificar y crear schema |
| `tests/e2e/test_schema_validation.py` | Smoke tests de schema (sin browser) |
| `tests/e2e/test_dataverse_access.py` | Tests de RBAC contra Dataverse |
| `tests/e2e/test_dataverse_workflow.py` | Tests E2E de todos los flujos operacionales |
| `tests/e2e/dataverse_support.py` | Seeders y helpers para tests Dataverse |
| `tests/e2e/pages/control_desv_page.py` | Page object: planillas calibres y semillas |
| `tests/e2e/pages/control_packing_page.py` | Page object: planilla calidad packing |

---

## Solución de problemas

### La tabla no se crea (`0x80040217` o `Does Not Exist`)

El App Registration no tiene permisos de **System Customizer** en Dataverse.
Asignarlo desde Power Platform Admin Center → Entornos → Usuarios → Roles.

### `PublishXml` falla con WARNING

No es crítico. Los cambios de schema pueden requerir publicación manual desde
Power Apps Studio → Soluciones → Publicar todas las personalizaciones.

### Tests de planillas fallan con `entity set not published`

Las planillas no existen aún en Dataverse. Ejecutar:

```bash
PERSISTENCE_BACKEND=dataverse python manage.py dataverse_ensure_schema --create \
  --table crf21_planilla_desv_calibre
```

### Timeout en creación de entidades

Normal. La Metadata API de Dataverse tarda 30–120s por tabla.
El command usa timeout de 180s. Si aún así falla, reintentar — es idempotente.

### Los tests se saltean sin correr

Verificar que `CALIPRO_TEST_BACKEND=dataverse` esté seteado.
Sin esta variable los tests hacen `pytest.skip` automáticamente.
