# Guía Rápida de Integración Dataverse

Esta guía resume lo esencial para operar con Microsoft Dataverse en este proyecto. Para ejemplos de ejecución y resultados, revisa los endpoints y los registros de pruebas ya generados.

---

## Configuración Básica

1. Variables de entorno en `.env` (ubicado en `python-app/src/`):
   - `DATAVERSE_URL`, `DATAVERSE_TENANT_ID`, `DATAVERSE_CLIENT_ID`, `DATAVERSE_CLIENT_SECRET`, `DATAVERSE_API_VERSION`, `DATAVERSE_TIMEOUT`
2. El archivo `config/settings/base.py` ya toma estas variables automáticamente.
3. El cliente principal es `DataverseClient` (`infrastructure/dataverse/client.py`), que maneja autenticación y errores.

---

## Endpoints Útiles

| Endpoint                              | Método | Propósito                        |
|----------------------------------------|--------|----------------------------------|
| `/api/dataverse/ping/`                 | GET    | Prueba conexión básica           |
| `/api/dataverse/discover/`             | GET    | Descubre entidades disponibles   |
| `/api/dataverse/bin/`                  | GET    | Acceso a tabla Bin               |
| `/api/dataverse/lote-planta/`          | GET    | Acceso a tabla LotePlanta        |
| `/api/dataverse/pallet/`               | GET    | Acceso a tabla Pallet            |

> Las tablas personalizadas deben estar publicadas y con permisos en el ambiente correcto.

---

## Entidades Principales

- **Bin**: unidad atómica del proceso
- **LotePlanta**: agrupación de bins
- **Pallet**: producto final

Tipos de datos: texto, número, fecha, booleano, lookup (relaciones).

---

## Troubleshooting (Resumen)

- **401 Unauthorized**: Revisa credenciales y permisos en Azure/Dataverse.
- **403 Forbidden**: El usuario/aplicación necesita permisos específicos.
- **404 Not Found**: Tabla no publicada, nombre incorrecto o ambiente equivocado. Usa `/api/dataverse/discover/`.
- **Timeout**: Aumenta `DATAVERSE_TIMEOUT` o limita campos/filas.

---

## Enlaces Útiles

- [Dataverse Web API Reference](https://docs.microsoft.com/en-us/power-apps/developer/data-platform/webapi/reference/about)
- [OData Query Options](https://docs.microsoft.com/en-us/power-apps/developer/data-platform/webapi/query-data-web-api)
- [Authentication Setup](https://docs.microsoft.com/en-us/power-apps/developer/data-platform/authenticate-web-api)
- [Power Platform Admin Center](https://admin.powerplatform.microsoft.com/)

---

*Última actualización: Marzo 2026 - Branch: `testing/dataverse`*
---

## Entidades Principales

- **Bin**: unidad atómica del proceso
- **LotePlanta**: agrupación de bins
- **Pallet**: producto final

Tipos de datos: texto, número, fecha, booleano, lookup (relaciones).

---

## Troubleshooting (Resumen)

- **401 Unauthorized**: Revisa credenciales y permisos en Azure/Dataverse.
- **403 Forbidden**: El usuario/aplicación necesita permisos específicos.
- **404 Not Found**: Tabla no publicada, nombre incorrecto o ambiente equivocado. Usa `/api/dataverse/discover/`.
- **Timeout**: Aumenta `DATAVERSE_TIMEOUT` o limita campos/filas.

---

## Enlaces Útiles

- [Dataverse Web API Reference](https://docs.microsoft.com/en-us/power-apps/developer/data-platform/webapi/reference/about)
- [OData Query Options](https://docs.microsoft.com/en-us/power-apps/developer/data-platform/webapi/query-data-web-api)
- [Authentication Setup](https://docs.microsoft.com/en-us/power-apps/developer/data-platform/authenticate-web-api)
- [Power Platform Admin Center](https://admin.powerplatform.microsoft.com/)

---

*Última actualización: Marzo 2026 - Branch: `testing/dataverse`*
    "$select": "id_bin,codigo_productor,kilos_neto_ingreso",
    "$orderby": "kilos_neto_ingreso desc",
    "$top": 50
})
```

### Consultas de Trazabilidad 

```python
# 9. Relaciones - Bins de un lote específico (usando expand si está configurado)
bins_del_lote = client.get("lote_plantas", params={
    "$filter": "id_lote_planta eq '20240328-L-0001'",
    "$expand": "bins($select=id_bin,bin_code,kilos_neto_ingreso)"
})

# 10. Conteos por estado
count_aprobados = client.get("bins/$count", params={
    "$filter": "a_o_r eq 'Aprobado'"
})
```

### Operadores OData Útiles

| Operador | Uso | Ejemplo |
|----------|-----|---------|
| `eq` | Igual | `name eq 'Empresa'` |
| `ne` | No igual | `statecode ne 1` |
| `gt` | Mayor que | `revenue gt 1000000` |
| `ge` | Mayor o igual | `createdon ge 2024-01-01` |
| `lt` | Menor que | `employees lt 100` |
| `le` | Menor o igual | `revenue le 500000` |
| `contains` | Contiene texto | `contains(name,'Export')` |
| `startswith` | Empieza con | `startswith(name,'A')` |
| `and` | Y lógico | `statecode eq 0 and revenue gt 0` |
| `or` | O lógico | `city eq 'Madrid' or city eq 'Barcelona'` |

---

## 🔄 Migración desde BD Local

### 1. Identificar Diferencias en Datos

```python
# Comparar estructura de datos local vs Dataverse
from django.contrib.contenttypes.models import ContentType
from operaciones.models import *  # tus modelos locales

# Lista tus modelos actuales
local_models = [
    # Ejemplo basado en tu estructura
    'RegistroEtapa',
    # Agrega tus otros modelos...
]

# Mapear a entidades Dataverse correspondientes
dataverse_mapping = {
    'RegistroEtapa': 'custom_registro_etapa',  # nombre en Dataverse
    # 'TuModelo': 'dataverse_entity_name'
}
```

### 2. Adaptar Consultas Existentes

**Antes (Django ORM):**
```python
from operaciones.models import RegistroEtapa

# Consulta local
registros = RegistroEtapa.objects.filter(
    tipo_evento='RECEPCION'
).order_by('-fecha_creacion')[:10]
```

**Después (Dataverse):**
```python
# Consulta Dataverse equivalente
registros = client.get("custom_registro_etapas", params={
    "$filter": "custom_tipo_evento eq 'RECEPCION'",
    "$orderby": "createdon desc", 
    "$top": 10
})
```

### 3. Migrar Servicios y Use Cases

```python
# Ejemplo: Adaptar un use case
class CrearLoteRecepcionUseCase:
    def __init__(self):
        self.dataverse_client = DataverseClient()
    
    def execute(self, data):
        # Antes: usar Django models
        # nuevo_lote = RegistroEtapa.objects.create(...)
        
        # Ahora: usar Dataverse
        nuevo_lote = self.dataverse_client.post("custom_lotes", json={
            "custom_nombre": data["nombre"],
            "custom_tipo_evento": "RECEPCION",
            "custom_fecha_creacion": datetime.now().isoformat()
        })
        
        return nuevo_lote
```

### 4. Actualizar Tests

```python
# Mockear cliente Dataverse en tests
from unittest.mock import Mock, patch

class TestDataverseIntegration(TestCase):
    @patch('infrastructure.dataverse.client.DataverseClient')
    def test_crear_lote_recepcion(self, mock_client):
        # Configurar mock
        mock_client_instance = Mock()
        mock_client.return_value = mock_client_instance
        mock_client_instance.post.return_value = {"id": "test-guid"}
        
        # Tu test aquí...
```

### 5. Probar Entidades del Modelo

Una vez configuradas las credenciales, puedes probar los endpoints específicos:

```bash
# Activar entorno virtual y navegar al proyecto
cd python-app/src
python manage.py runserver

# En otra terminal o navegador, probar:
```

**Endpoints de prueba disponibles:**

|                        URL                         |         Propósito           |
|----------------------------------------------------|-----------------------------|
| `http://127.0.0.1:8000/api/dataverse/ping/`        | Prueba conexión básica      |
| `http://127.0.0.1:8000/api/dataverse/bin/`         | **Probar tabla Bin**        |
| `http://127.0.0.1:8000/api/dataverse/lote-planta/` | **Probar tabla LotePlanta** |
| `http://127.0.0.1:8000/api/dataverse/pallet/`      | **Probar tabla Pallet**     |

> 🎯 **Los endpoints específicos del modelo** intentarán encontrar automáticamente el nombre correcto de la entidad en tu entorno Dataverse probando nombres comunes como `bins`, `custom_bins`, `new_bins`, etc.

---

## 🛠 Troubleshooting

### Errores Comunes

#### 1. **Error 401 - Unauthorized**
```
DataverseAPIError: Dataverse devolvió 401 en GET ...
```
**Soluciones:**
- ✅ Verifica las credenciales en `.env`
- ✅ Confirma que el Client ID tiene permisos en Dataverse 
- ✅ Revisa que el tenant ID sea correcto
- ✅ Verifica que el Application esté registrado en Azure AD

#### 2. **Error 403 - Forbidden**  
**Soluciones:**
- ✅ El usuario/aplicación necesita permisos específicos en Dataverse
- ✅ Contacta al administrador para asignar roles de seguridad adecuados

#### 3. **Error 404 - Not Found**
```
DataverseAPIError: Dataverse devolvió 404 en GET /api/data/v9.2/bins
```
**Soluciones:**
- ✅ **Verificar ambiente**: ¿Estás en Development o Production?
- ✅ **Verificar publicación**: Las tablas deben estar publicadas en solución
- ✅ **Usar descubrimiento**: `GET /api/dataverse/discover/` para ver qué está disponible
- ✅ Confirma el nombre exacto de la entidad (puede ser personalizado)
- ✅ Usa los endpoints de testing: `/api/dataverse/bin/` para descubrir el nombre correcto
- ✅ Revisa que la versión de API sea compatible

**🔍 Descubrir nombres de entidades:**
```python
# Los endpoints de testing prueban automáticamente nombres comunes:
# Para Bin: ["bins", "custom_bins", "new_bins", "cr4d2_bins"]
# Para LotePlanta: ["lote_plantas", "custom_lote_plantas", "new_lote_plantas", "cr4d2_lote_plantas", "loteplanta"]
# Para Pallet: ["pallets", "custom_pallets", "new_pallets", "cr4d2_pallets"]

# Una vez que encuentres el nombre correcto, úsalo en tus consultas:
client.get("nombre_correcto_encontrado", params={"$top": 5})
```

#### 5. **Tablas no disponibles en el ambiente actual**
**Síntomas:**
- El endpoint `/api/dataverse/discover/` no encuentra las entidades del MVP
- Error 404 en todas las variantes de nombres

**Soluciones:**
- ✅ **Contacta al administrador** de Power Platform para:
  - Confirmar en qué ambiente están las tablas
  - Verificar que estén publicadas
  - Revisar permisos de acceso
- ✅ **Verifica la URL**: ¿Apuntas al ambiente correcto?
- ✅ **Revisar soluciones**: Las tablas pueden estar en una solución sin publicar

#### 6. **Timeout Errors**
**Soluciones:**  
- ✅ Aumenta `DATAVERSE_TIMEOUT` en `.env`
- ✅ Implementa paginación para consultas grandes
- ✅ Usa `$select` para limitar campos retornados

#### 7. **Rate Limiting**
**Soluciones:**  
- ✅ Implementa retry con backoff exponencial
- ✅ Reduce la frecuencia de llamadas API
- ✅ Usa batch requests cuando sea posible

### Debugging

```python
# 1. Habilitar logs detallados
import logging
logging.basicConfig(level=logging.DEBUG)

# 2. Probar conexión básica
try:
    client = DataverseClient()
    result = client.get("WhoAmI")
    print(f"Conectado como: {result}")
except Exception as e:
    print(f"Error de conexión: {e}")

# 3. Verificar configuración
from django.conf import settings
print(f"URL: {settings.DATAVERSE_URL}")
print(f"Tenant: {settings.DATAVERSE_TENANT_ID}")
print(f"Client ID: {settings.DATAVERSE_CLIENT_ID}")
print(f"Version: {settings.DATAVERSE_API_VERSION}")
```

### Enlaces Útiles

-  [Dataverse Web API Reference](https://docs.microsoft.com/en-us/power-apps/developer/data-platform/webapi/reference/about)
- 🔍 [OData Query Options](https://docs.microsoft.com/en-us/power-apps/developer/data-platform/webapi/query-data-web-api)
- 🔐 [Authentication Setup](https://docs.microsoft.com/en-us/power-apps/developer/data-platform/authenticate-web-api)
- 🛠 [Power Platform Admin Center](https://admin.powerplatform.microsoft.com/)

---

*Última actualización: Marzo 2026 - Branch: `testing/dataverse`*