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
 
> Importante: en el estado revisado, la integración Dataverse está orientada a **conectividad, validación de tablas y pruebas iniciales**, no a una API funcional completa del dominio.
 
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
 
- Recorre una lista fija de tablas Dataverse, que actualmente considera las 14 tablas implementadas en Dataverse.
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
 
El endpoint `check_tables/` trabaja con esta lista fija de tablas:
 
1. `crf21_bins`
2. `crf21_calidad_desverdizados`
3. `crf21_camara_mantencions`
4. `crf21_lote_plantas`
5. `crf21_bin_lote_plantas`
6. `crf21_calidad_pallets`
7. `crf21_camara_frios`
8. `crf21_control_proceso_packings`
9. `crf21_desverdizados`
10. `crf21_ingreso_packings`
11. `crf21_lote_planta_pallets`
12. `crf21_medicion_temperatura_salidas`
13. `crf21_pallets`
14. `crf21_registro_packings`
 
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
 
- configuración Dataverse vía `.env`
- selector `PERSISTENCE_BACKEND`
- cliente Dataverse funcional con métodos tipados
- endpoint de ping, chequeo de tablas y dos endpoints de prueba sobre bins
 
### Actualmente no existe
 
- endpoint `/discover/`
- endpoints `/bin/`, `/lote-planta/`, `/pallet/`
- capa REST completa por entidad del dominio
- contrato final de sincronización total entre Django y Dataverse
 
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

## 16. Última actualización

Marzo 2026  
Alineado a los commits:

- `ebdd41d084a8a0a398e34b01a4c5540ec2cc104e`
- `2493a804bc7dc5b514fb7478e3c52f88588eeb85`
