# Testing contra Dataverse

Guia para validar schema, acceso y flujos del backend usando Dataverse real.

## Prerrequisitos

Variables requeridas:

```env
PERSISTENCE_BACKEND=dataverse
CALIPRO_TEST_BACKEND=dataverse
DATAVERSE_URL=https://<org>.crm.dynamics.com
DATAVERSE_TENANT_ID=<tenant-id>
DATAVERSE_CLIENT_ID=<client-id>
DATAVERSE_CLIENT_SECRET=<client-secret>
```

Ejecutar desde `python-app/`.

## Secuencia recomendada

1. Verificar schema
2. Corregir gaps de schema
3. Ejecutar smoke tests de schema
4. Ejecutar tests de acceso y permisos
5. Ejecutar tests E2E de flujos

## Fase 1: verificar schema

```bash
PERSISTENCE_BACKEND=dataverse python manage.py dataverse_ensure_schema --check-only
```

Validacion por tabla:

```bash
PERSISTENCE_BACKEND=dataverse python manage.py dataverse_ensure_schema --check-only --table crf21_planilla_desv_calibre
```

## Fase 2: crear entidades/campos faltantes

Crear todo:

```bash
PERSISTENCE_BACKEND=dataverse python manage.py dataverse_ensure_schema --create
```

Crear por tabla:

```bash
PERSISTENCE_BACKEND=dataverse python manage.py dataverse_ensure_schema --create --table crf21_planilla_desv_calibre
PERSISTENCE_BACKEND=dataverse python manage.py dataverse_ensure_schema --create --table crf21_planilla_desv_semillas
PERSISTENCE_BACKEND=dataverse python manage.py dataverse_ensure_schema --create --table crf21_planilla_calidad_packing
PERSISTENCE_BACKEND=dataverse python manage.py dataverse_ensure_schema --create --table crf21_planilla_calidad_camara
```

## Fase 3: smoke tests de schema

```bash
CALIPRO_TEST_BACKEND=dataverse pytest tests/e2e/test_schema_validation.py -v
```

## Fase 4: permisos y acceso

```bash
CALIPRO_TEST_BACKEND=dataverse pytest tests/e2e/test_dataverse_access.py -v
```

## Fase 5: flujos E2E

```bash
CALIPRO_TEST_BACKEND=dataverse pytest tests/e2e/test_dataverse_workflow.py -v
```

## Suite completa

```bash
CALIPRO_TEST_BACKEND=dataverse pytest \
  tests/e2e/test_schema_validation.py \
  tests/e2e/test_dataverse_access.py \
  tests/e2e/test_dataverse_workflow.py \
  -v --tb=short
```

## Archivos clave

- `src/infrastructure/dataverse/schema_definition.py`
- `src/core/management/commands/dataverse_ensure_schema.py`
- `tests/e2e/test_schema_validation.py`
- `tests/e2e/test_dataverse_access.py`
- `tests/e2e/test_dataverse_workflow.py`

## Problemas frecuentes

### Error de permisos (`403`)

El app registration necesita permisos de seguridad suficientes en Dataverse.

### Entity set no publicado

Reintentar `dataverse_ensure_schema --create` y publicar personalizaciones en Power Apps si aplica.

### Timeout en metadata

La creacion de entidades puede demorar; reintentar es seguro porque el comando es idempotente.
