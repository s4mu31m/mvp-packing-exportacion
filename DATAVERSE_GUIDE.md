# Guia Dataverse

Guia operativa de integracion Dataverse para el backend Django del proyecto.

> Documentacion funcional y de arquitectura: <https://github.com/s4mu31m/mvp-packing-exportacion/wiki>

## Alcance de este documento

Este documento cubre solo la operacion tecnica local:

- configuracion de entorno Dataverse;
- endpoints de diagnostico expuestos por Django;
- entity sets utilizados por la capa de repositorios;
- scripts y comandos de verificacion;
- limites tecnicos conocidos de la integracion.

## Configuracion de entorno

Define estas variables en `python-app/.env`:

```env
PERSISTENCE_BACKEND=dataverse
DATAVERSE_URL=https://<org>.crm.dynamics.com
DATAVERSE_TENANT_ID=<tenant-id>
DATAVERSE_CLIENT_ID=<client-id>
DATAVERSE_CLIENT_SECRET=<client-secret>
DATAVERSE_API_VERSION=v9.2
DATAVERSE_TIMEOUT=30
```

## Rutas Dataverse en el proyecto

`python-app/src/config/urls.py` monta Dataverse en:

- `/api/dataverse/ping/`
- `/api/dataverse/check_tables/`
- `/api/dataverse/save_first_bin_code/`
- `/api/dataverse/get_first_bin_code/`

## Capa de integracion implementada

Componentes principales:

- Cliente OData: `python-app/src/infrastructure/dataverse/client.py`
- Mapeo de schema: `python-app/src/infrastructure/dataverse/mapping.py`
- Repositorios Dataverse: `python-app/src/infrastructure/dataverse/repositories/__init__.py`
- Factory de backend: `python-app/src/infrastructure/repository_factory.py`

La aplicacion comparte casos de uso para ambos backends (`sqlite` y `dataverse`).

## Entity sets usados por el backend

Fuente: `mapping.py`.

1. `crf21_bins`
2. `crf21_lote_plantas`
3. `crf21_pallets`
4. `crf21_bin_lote_plantas`
5. `crf21_lote_planta_pallets`
6. `crf21_camara_mantencions`
7. `crf21_desverdizados`
8. `crf21_calidad_desverdizados`
9. `crf21_ingreso_packings`
10. `crf21_registro_packings`
11. `crf21_control_proceso_packings`
12. `crf21_calidad_pallets`
13. `crf21_camara_frios`
14. `crf21_medicion_temperatura_salidas`
15. `crf21_usuariooperativos`
16. `crf21_calidad_pallet_muestras`
17. `crf21_planilla_desv_calibres`
18. `crf21_planilla_desv_semillas`
19. `crf21_planilla_calidad_packings`
20. `crf21_planilla_calidad_camaras`

## Verificacion rapida

Desde `python-app/src` con servidor levantado:

```bash
curl http://127.0.0.1:8000/api/dataverse/ping/
curl http://127.0.0.1:8000/api/dataverse/check_tables/
```

## Scripts de diagnostico

Scripts disponibles en `scripts/dataverse/` (ejecutar desde la raiz del repo):

```bash
python scripts/dataverse/run_all.py
python scripts/dataverse/02_check_tables.py
python scripts/dataverse/07_validate_mapping.py
python scripts/dataverse/11_validate_e2e.py
```

## Limites tecnicos conocidos

- `RegistroEtapa` no tiene tabla dedicada en Dataverse; su repositorio en Dataverse es no-op con log local.
- El estado operativo del lote no depende de un campo `estado` en Dataverse; se trabaja con `etapa_actual` y reglas de flujo.
- Los correlativos en Dataverse se calculan por conteo de registros, por lo que no son atomicos bajo concurrencia alta.
- Dataverse Web API no ofrece transaccion ACID equivalente a la del ORM local.

## Troubleshooting

### 401 / autenticacion

- revisar `DATAVERSE_CLIENT_ID`, `DATAVERSE_CLIENT_SECRET`, `DATAVERSE_TENANT_ID`.
- confirmar permisos del app registration en el ambiente Dataverse.

### 403 / permisos

- verificar roles de seguridad en Power Platform para lectura/escritura de tablas requeridas.

### 404 / tabla o ruta

- confirmar que el entorno es correcto (`DATAVERSE_URL`).
- validar tablas con `/api/dataverse/check_tables/`.

### timeout

- ajustar `DATAVERSE_TIMEOUT`.
- reducir volumen de consulta con `select`, `top` y filtros.

## Referencias

- Web API Dataverse: <https://learn.microsoft.com/power-apps/developer/data-platform/webapi/overview>
- OData en Dataverse: <https://learn.microsoft.com/power-apps/developer/data-platform/webapi/query-data-web-api>
- Administracion Power Platform: <https://admin.powerplatform.microsoft.com/>
