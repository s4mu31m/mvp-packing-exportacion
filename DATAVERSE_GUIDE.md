# Guía Rápida de Integración Dataverse
 
Esta guía quedó corregida para alinearse con el código implementado en los commits:
 
- `ebdd41d084a8a0a398e34b01a4c5540ec2cc104e`
- `2493a804bc7dc5b514fb7478e3c52f88588eeb85`
 
Su objetivo es documentar **solo** lo que realmente existe en la integración Dataverse revisada, sin asumir endpoints, discovery ni operaciones que todavía no están implementadas.
 
---
 
## 1. Alcance real de esta guía
 
Esta guía **sí** cubre:
 
- configuración Dataverse cargada desde `.env`,
- cliente Dataverse implementado en el backend Django,
- endpoints de prueba actualmente disponibles,
- validación de acceso a las tablas Dataverse del modelo del MVP,
- ejemplos de uso alineados con los métodos reales del cliente.
 
Esta guía **no** cubre todavía:
 
- endpoints REST por recurso como `/bin/`, `/lote-planta/` o `/pallet/`,
- discovery genérico de entidades vía endpoint propio,
- sincronización completa entre modelo Django y Dataverse,
- capa funcional final del dominio apoyada totalmente en Dataverse.
 
> Importante: la integración Dataverse está **operativa para el flujo MVP completo**. Las 16 tablas del modelo tienen repositorios implementados (SQLite + Dataverse). Los límites conocidos y el único gap bloqueante pendiente están documentados en la sección 17 y en [`docs/cierre-mvp/limites-aceptados-mvp.md`](docs/cierre-mvp/limites-aceptados-mvp.md).
 
---
 
## 2. Configuración básica
 
Las variables de entorno usadas por el proyecto son:
 
- `DATAVERSE_URL`
- `DATAVERSE_TENANT_ID`
- `DATAVERSE_CLIENT_ID`
- `DATAVERSE_CLIENT_SECRET`
- `DATAVERSE_API_VERSION`
- `DATAVERSE_TIMEOUT`
- `PERSISTENCE_BACKEND`
 
### Ejemplo de `.env`
 
```env
DATAVERSE_URL=https://TU-AMBIENTE.crm.dynamics.com
DATAVERSE_TENANT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
DATAVERSE_CLIENT_ID=xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx
DATAVERSE_CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxx
DATAVERSE_API_VERSION=v9.2
DATAVERSE_TIMEOUT=30
PERSISTENCE_BACKEND=dataverse
```
 
### Qué hace cada variable
 
- `DATAVERSE_URL`: URL base del ambiente Dataverse.
- `DATAVERSE_TENANT_ID`: tenant de Azure / Entra ID.
- `DATAVERSE_CLIENT_ID`: identificador de la aplicación registrada.
- `DATAVERSE_CLIENT_SECRET`: secreto de cliente de la aplicación.
- `DATAVERSE_API_VERSION`: versión de la Web API. En el código revisado el valor por defecto es `v9.2`.
- `DATAVERSE_TIMEOUT`: timeout de lectura usado por el cliente.
- `PERSISTENCE_BACKEND`: selector de backend de persistencia. El comentario del settings indica `sqlite` para desarrollo local y `dataverse` para usar Microsoft Dataverse vía Web API.
 
---
 
## 3. Rutas montadas en el proyecto
 
El proyecto monta las rutas Dataverse bajo el prefijo:
 
```text
/api/dataverse/
```
 
Esto significa que los endpoints definidos en `core/dataverse_urls.py` quedan expuestos bajo ese prefijo.
 
---
 
## 4. Endpoints realmente disponibles
 
Los endpoints reales que existen en los commits revisados son estos:
 
| Endpoint | Método | Propósito real actual |
|---|---|---|
| `/api/dataverse/ping/` | GET | Verifica autenticación y conexión básica con Dataverse usando `WhoAmI()` |
| `/api/dataverse/check_tables/` | GET | Revisa si las tablas configuradas del modelo están accesibles y devuelve muestra del primer registro cuando exista |
> Nota: Este endpoint, además de indicar si cada tabla está accesible, incluye en la respuesta todos los campos y valores del primer registro encontrado (si existe) para cada tabla. Esto permite visualizar la estructura real y ejemplos de datos de cada entidad, facilitando el desarrollo y la validación del modelo.
| `/api/dataverse/save_first_bin_code/` | POST | Consulta el primer registro de `crf21_bins` y devuelve su `crf21_bin_code` en JSON |
| `/api/dataverse/get_first_bin_code/` | GET | Consulta el primer registro de `crf21_bins` y devuelve su `crf21_bin_code` en JSON |
 
### Endpoints que **no** existen en estos commits
 
No deben documentarse como disponibles porque no aparecen implementados en `dataverse_urls.py` ni en `dataverse_views.py`:
 
- `/api/dataverse/discover/`
- `/api/dataverse/bin/`
- `/api/dataverse/lote-planta/`
- `/api/dataverse/pallet/`
 
---
 
## 5. Comportamiento real de cada endpoint
 
### 5.1 `GET /api/dataverse/ping/`
 
Prueba la conexión básica con Dataverse.
 
#### Flujo actual
 
1. Instancia `DataverseClient()`.
2. Llama `client.whoami()`.
3. Retorna un JSON con:
   - `status`
   - `message`
   - `user_id`
   - `organization_id`
   - `business_unit_id`
 
#### Uso esperado
 
Se usa como prueba rápida de autenticación, conectividad y acceso mínimo a la API.
 
---
 
### 5.2 `GET /api/dataverse/check_tables/`
 
Valida si las tablas definidas por el proyecto están accesibles.
 
#### Qué hace
 
- Recorre una lista fija de tablas Dataverse, que actualmente considera las 16 tablas activas del modelo.
- Para cada tabla, llama `client.list_rows(entity_set_name=table, top=1)`.
- Si la tabla responde, marca `accessible: true`.
- Si hay al menos un registro, devuelve `sample_count`, `pk` y `sample_record`.
- Si falla, deja `accessible: false` y el `error` correspondiente.
 
#### Qué **no** hace
 
- No descubre automáticamente todas las entidades del ambiente.
- No resuelve nombres alternativos.
- No prueba variantes como `custom_*`, `new_*` o similares.
 
Es un chequeo cerrado sobre una lista fija ya conocida por el proyecto.
 
---
 
### 5.3 `POST /api/dataverse/save_first_bin_code/`
 
Consulta el primer registro de `crf21_bins` y extrae el campo `crf21_bin_code`.
 
#### Respuesta actual
 
```json
{
  "status": "success",
  "bin_code": "VALOR_ENCONTRADO",
  "mensaje": "El bin code de bin es: VALOR_ENCONTRADO"
}
```
 
> Aunque el docstring menciona guardar el valor en un archivo local, en la implementación revisada el endpoint solo consulta Dataverse y responde en JSON. No se observa persistencia efectiva en archivo dado que se eliminó al ser una prueba local.
 
---
 
### 5.4 `GET /api/dataverse/get_first_bin_code/`
 
Consulta el primer registro disponible en `crf21_bins` y responde solo con el `bin_code`.
 
#### Respuesta esperada
 
```json
{
  "bin_code": "VALOR_ENCONTRADO"
}
```
 
Si no hay registros o no existe el campo, responde con error 404.
 
---
 
## 6. Tablas Dataverse consideradas por la integración actual
 
El endpoint `check_tables/` trabaja con esta lista fija de tablas (16 activas validadas
el 2026-04-04 via `scripts/dataverse/07_validate_mapping.py`):

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
16. `crf21_calidad_pallet_muestras` *(creada 2026-04-04 via Metadata API)*

Tablas aceptadas como no-op (no existen en Dataverse intencionalmente):

- `crf21_registro_etapas` — trazabilidad de etapas, gap conocido Issue #39.
  Los repositorios operan sin esta tabla; `DataverseRegistroEtapaRepository` es no-op.
 
---
 
## 7. Cliente Dataverse implementado
 
```python
DataverseClient
# python-app/src/infrastructure/dataverse/client.py
```
 
### Responsabilidades
 
- construir la URL base de la Web API,
- adjuntar el token Bearer,
- refrescar token ante `401`,
- ejecutar requests HTTP,
- encapsular errores con `DataverseAPIError`.
 
### Métodos públicos reales
 
- `whoami()`
- `get_entity_definition(logical_name)`
- `list_rows(entity_set_name, select=None, filter_expr=None, top=50, orderby=None, expand=None)`
- `create_row(entity_set_name, payload)`
- `update_row(entity_set_name, row_id, payload)`
 
> Esta guía no documenta métodos genéricos `get()` o `post()` porque no son la interfaz pública real expuesta por el cliente revisado.
 
---
 
## 8. Ejemplos de uso alineados al cliente real
 
### 8.1 Verificar conexión
 
```python
from infrastructure.dataverse.client import DataverseClient
 
client = DataverseClient()
result = client.whoami()
print(result)
```
 
### 8.2 Listar bins
 
```python
from infrastructure.dataverse.client import DataverseClient
 
client = DataverseClient()
 
rows = client.list_rows(
    entity_set_name="crf21_bins",
    select=["crf21_bin_code"],
    top=5,
)
print(rows)
```
 
### 8.3 Filtrar y ordenar registros
 
```python
rows = client.list_rows(
    entity_set_name="crf21_bins",
    select=["crf21_bin_code"],
    filter_expr="crf21_bin_code ne null",
    top=10,
    orderby="createdon desc",
)
```
 
### 8.4 Expand — bins de un lote planta
 
```python
rows = client.list_rows(
    entity_set_name="crf21_lote_plantas",
    filter_expr="crf21_lote_plantaid eq '20240328-L-0001'",
    expand="crf21_bin_lote_plantas($select=crf21_bin_code)",
    top=50,
)
```
 
### 8.5 Conteo por estado
 
```python
# Filtrar y contar en Python si el endpoint $count no está habilitado
rows = client.list_rows(
    entity_set_name="crf21_bins",
    filter_expr="statecode eq 0",
    select=["crf21_bin_code"],
    top=1000,
)
total_activos = len(rows)
```
 
### 8.6 Crear un registro
 
```python
created = client.create_row("crf21_bins", {
    "crf21_bin_code": "BIN-TEST-0001"
})
```
 
### 8.7 Actualizar un registro
 
```python
client.update_row("crf21_bins", "GUID-DEL-REGISTRO", {
    "crf21_bin_code": "BIN-TEST-0001-ACTUALIZADO"
})
```
 
### 8.8 Metadata de una entidad
 
```python
definition = client.get_entity_definition("crf21_bin")
```
 
> `get_entity_definition()` usa el logical name; `list_rows()` usa el entity set name.
 
---
 
## 9. Referencia de operadores OData
 
Útil al construir `filter_expr` en `list_rows()`:
 
| Operador | Uso | Ejemplo |
|----------|-----|---------|
| `eq` | Igual | `crf21_bin_code eq 'BIN-001'` |
| `ne` | No igual | `statecode ne 1` |
| `gt` | Mayor que | `createdon gt 2024-01-01` |
| `ge` | Mayor o igual | `createdon ge 2024-01-01` |
| `lt` | Menor que | `statecode lt 2` |
| `le` | Menor o igual | `statecode le 1` |
| `contains` | Contiene texto | `contains(crf21_bin_code,'TEST')` |
| `startswith` | Empieza con | `startswith(crf21_bin_code,'BIN')` |
| `and` | Y lógico | `statecode eq 0 and crf21_bin_code ne null` |
| `or` | O lógico | `statecode eq 0 or statecode eq 1` |
 
---
 
## 10. Migración desde BD Local
 
Esta sección orienta cómo reemplazar consultas Django ORM existentes por llamadas al cliente Dataverse real.
 
### Adaptar consultas
 
**Antes (Django ORM):**
```python
from operaciones.models import RegistroEtapa
 
registros = RegistroEtapa.objects.filter(
    tipo_evento='RECEPCION'
).order_by('-fecha_creacion')[:10]
```
 
**Después (Dataverse):**
```python
registros = client.list_rows(
    entity_set_name="crf21_registro_packings",
    filter_expr="crf21_tipo_evento eq 'RECEPCION'",
    orderby="createdon desc",
    top=10,
)
```
 
### Migrar use cases
 
```python
class CrearLoteRecepcionUseCase:
    def __init__(self):
        self.client = DataverseClient()
 
    def execute(self, data):
        return self.client.create_row("crf21_lote_plantas", {
            "crf21_nombre": data["nombre"],
            "crf21_tipo_evento": "RECEPCION",
        })
```
 
### Mockear en tests
 
```python
from unittest.mock import Mock, patch
 
class TestDataverseIntegration(TestCase):
    @patch('infrastructure.dataverse.client.DataverseClient')
    def test_crear_lote_recepcion(self, mock_client):
        mock_instance = Mock()
        mock_client.return_value = mock_instance
        mock_instance.create_row.return_value = {"id": "test-guid"}
        # Tu test aquí...
```
 
---
 
## 11. Cómo probar la integración en local
 
```bash
cd python-app/src
python manage.py runserver
```
 
| URL | Propósito |
|-----|-----------|
| `http://127.0.0.1:8000/api/dataverse/ping/` | Verifica autenticación |
| `http://127.0.0.1:8000/api/dataverse/check_tables/` | Revisa acceso a tablas del modelo |
| `http://127.0.0.1:8000/api/dataverse/get_first_bin_code/` | Lee primer bin |
| `curl -X POST http://127.0.0.1:8000/api/dataverse/save_first_bin_code/` | Prueba POST sobre primer bin |
 
---
 
## 12. Troubleshooting
 
### Error 401 - Unauthorized
 
- Revisa `DATAVERSE_CLIENT_ID`, `DATAVERSE_CLIENT_SECRET`, `DATAVERSE_TENANT_ID`
- Verifica que la app esté registrada en Azure / Entra ID con los permisos correctos
 
### Error 403 - Forbidden
 
- Revisa roles de seguridad en Dataverse
- Verifica permisos de lectura/escritura sobre las tablas y el ambiente
 
### Error 404 - Not Found
 
- Confirma que el ambiente sea el correcto
- Verifica que las tablas estén publicadas
- Confirma que el prefijo `crf21_` corresponda al publisher real
- No existe un endpoint de discovery general; usa `check_tables/` para validar
 
### Timeout
 
- Aumenta `DATAVERSE_TIMEOUT` en `.env`
- Usa `select` para limitar campos y `top` para limitar filas
 
### Rate Limiting
 
- Implementa retry con backoff exponencial
- Usa batch requests cuando sea posible
 
### Debugging
 
```python
import logging
logging.basicConfig(level=logging.DEBUG)
 
client = DataverseClient()
try:
    result = client.whoami()
    print(f"Conectado como: {result}")
except Exception as e:
    print(f"Error: {e}")
 
from django.conf import settings
print(settings.DATAVERSE_URL)
print(settings.DATAVERSE_TENANT_ID)
print(settings.DATAVERSE_CLIENT_ID)
print(settings.DATAVERSE_API_VERSION)
```
 
---
 
## 13. Estado actual resumido
 
### Actualmente existe

- Configuracion Dataverse via `.env`
- Selector `PERSISTENCE_BACKEND` (sqlite / dataverse)
- Cliente Dataverse funcional con metodos tipados
- Endpoints de ping, chequeo de tablas y prueba sobre bins
- **16 tablas activas en Dataverse** con repositorios implementados (SQLite + Dataverse)
- `CalidadPalletMuestra`: tabla creada 2026-04-04 via Metadata API;
  `DataverseCalidadPalletMuestraRepository` y `SqliteCalidadPalletMuestraRepository`
  operativos; `_save_muestras` migrado al repo layer en `PaletizadoView`
- Scripts standalone de diagnostico en `scripts/dataverse/` (00–09 + run_all.py)
- 100% de mapeo de campos validado via `07_validate_mapping.py`

### Actualmente no existe / gaps conocidos

- Endpoint `/discover/`
- Endpoints REST por entidad (`/bin/`, `/lote-planta/`, `/pallet/`)
- `crf21_registro_etapas` — no existe en Dataverse; `DataverseRegistroEtapaRepository`
  es no-op (log local). No es un bloqueante operativo.
- Atomicidad en `DataverseSequenceCounterRepository` — race condition bajo alta
  concurrencia. Aceptable para la escala del MVP.
 
---
 
## 14. Recomendaciones siguientes
 
1. Renombrar `save_first_bin_code/` si su propósito seguirá siendo solo de prueba.
2. Separar endpoints de infraestructura de endpoints funcionales del dominio.
3. Definir contractualmente qué casos de uso leerán o escribirán en Dataverse.
4. Agregar tests unitarios y de integración específicos de Dataverse.
5. Documentar una guía funcional separada para la API real del MVP.
 
---
 
## 15. Referencias
 
- [Dataverse Web API Reference](https://docs.microsoft.com/en-us/power-apps/developer/data-platform/webapi/reference/about)
- [OData Query Options](https://docs.microsoft.com/en-us/power-apps/developer/data-platform/webapi/query-data-web-api)
- [Authentication Setup](https://docs.microsoft.com/en-us/power-apps/developer/data-platform/authenticate-web-api)
- [Power Platform Admin Center](https://admin.powerplatform.microsoft.com/)
 
---

## 16. Scripts de diagnostico standalone

Los scripts en `scripts/dataverse/` permiten diagnosticar el estado de Dataverse
sin levantar el servidor Django. Cargan credenciales desde `.env` automaticamente.

```bash
# Ejecutar desde la raiz del repositorio
python scripts/dataverse/run_all.py        # Suite completa (00-07)
python scripts/dataverse/02_check_tables.py # Solo verificacion de tablas
python scripts/dataverse/07_validate_mapping.py  # Validar campos vs esquema real
python scripts/dataverse/09_create_calidad_pallet_muestras.py  # Crear tabla CPM
```

| Script | Proposito |
|--------|-----------|
| `00_check_env.py` | Verifica variables de entorno |
| `01_whoami.py` | Prueba autenticacion OAuth2 |
| `02_check_tables.py` | Verifica existencia y conteo de las 16 tablas |
| `03_query_bins.py` | Consulta ultimos 10 bins |
| `04_query_lotes.py` | Consulta ultimos 10 lotes |
| `05_query_pallets.py` | Consulta ultimos 10 pallets |
| `06_query_usuarios.py` | Lista operadores (sin password hash) |
| `07_validate_mapping.py` | Valida campos del mapping.py vs esquema Dataverse |
| `09_create_calidad_pallet_muestras.py` | Crea/verifica tabla crf21_calidad_pallet_muestras |

---

## 17. Límites aceptados del MVP

Los siguientes gaps son conocidos y aceptados para la escala del MVP.
No son bugs — son compromisos de diseño documentados.

### RegistroEtapa es no-op en Dataverse
La tabla `crf21_registro_etapas` no existe en Dataverse.
`DataverseRegistroEtapaRepository` escribe únicamente en log local sin persistir en Dataverse.
La trazabilidad de etapas queda disponible en SQLite local únicamente.

### Campo `estado` del lote no existe en Dataverse
`crf21_lote_plantas` no tiene campo `estado`.
Al leer un lote desde Dataverse se retorna `estado="abierto"` por defecto.
`repos.lotes.update(..., {"estado": "cerrado"})` es ignorado silenciosamente.
El cierre efectivo del lote se controla por session pop en `RecepcionView`.

El progreso operativo del lote **sí** se persiste en Dataverse a través del campo
`etapa_actual` (`crf21_etapa_actual`), que se actualiza en cada etapa del flujo
(p.ej. `"Calidad Pallet"`, `"Cámara Frío"`). `etapa_actual` está incluido en
`_updatable` de `DataverseLoteRepository.update()` y se sincroniza normalmente.

### `SequenceCounterRepository` no es atómico en Dataverse
`DataverseSequenceCounterRepository` genera correlativos contando registros existentes
via OData (sin tabla de secuencias dedicada). Bajo alta concurrencia puede haber
race conditions que generen correlativos duplicados.
Aceptable para operación secuencial del MVP (un operador por flujo).

### CalidadPalletMuestra sincroniza a Dataverse desde 2026-04-04
La tabla `crf21_calidad_pallet_muestras` fue creada el 2026-04-04.
Registros de muestras creados antes de esa fecha existen solo en SQLite local.
A partir de esa fecha, la persistencia opera via `repos.calidad_pallet_muestras`
según `PERSISTENCE_BACKEND`.

---

## 18. Ultima actualizacion

Abril 2026
Alineado al estado del repositorio validado el 2026-04-04:
- 16 tablas activas con repositorios completos
- crf21_calidad_pallet_muestras creada via Metadata API
- Scripts de diagnostico validados contra el ambiente real
