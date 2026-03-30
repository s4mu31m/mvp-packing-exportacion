# Endpoints de Prueba para Dataverse

Este archivo contiene las instrucciones para probar la conexión con Dataverse.

## Configuración Inicial

1. **Edita el archivo `.env`** con las credenciales reales que te proporcionó tu compañero:

```bash
# En el archivo src/.env
DATAVERSE_URL=https://tu-org.api.crm.dynamics.com
DATAVERSE_TENANT_ID=tu-tenant-id-real
DATAVERSE_CLIENT_ID=tu-client-id-real  
DATAVERSE_CLIENT_SECRET=tu-client-secret-real
```

2. **Activa el entorno virtual**:

```bash
# En Windows
.venv\Scripts\activate

# Navega a la carpeta src
cd src
```

3. **Ejecuta el servidor de desarrollo**:

```bash
cd mvp-packing-exportacion/python-app/src
python manage.py runserver
```

## Endpoints Disponibles

Una vez que el servidor esté corriendo, puedes probar estos endpoints:

### 1. Ping a Dataverse (Prueba de Conexión)
```
GET http://127.0.0.1:8000/api/dataverse/ping/
```

**¿Qué hace?**: Verifica que puedes autenticarte y conectarte a Dataverse obteniendo información del usuario actual.

**Respuesta esperada si funciona**:
```json
{
    "status": "success",
    "message": "Conexión exitosa a Dataverse",
    "user_id": "xxx-xxx-xxx",
    "organization_id": "xxx-xxx-xxx", 
    "business_unit_id": "xxx-xxx-xxx"
}
```

### 2. Consultar Cuentas (Accounts)
```
GET http://127.0.0.1:8000/api/dataverse/accounts/
```

**¿Qué hace?**: Intenta consultar las primeras 5 cuentas en Dataverse para probar que puedes leer datos.

### 3. Probar Entidades disponibles
```
GET http://127.0.0.1:8000/api/dataverse/entities/
```

**¿Qué hace?**: Prueba el acceso a entidades comunes (accounts, contacts, systemusers) para ver cuáles están disponibles.

## Formas de Probar

### Opción 1: En el navegador
Simplemente abre tu navegador y ve a:
- http://127.0.0.1:8000/api/dataverse/ping/
- http://127.0.0.1:8000/api/dataverse/accounts/
- http://127.0.0.1:8000/api/dataverse/entities/

### Opción 2: Usando PowerShell/Terminal
```powershell
# Prueba de conexión
curl http://127.0.0.1:8000/api/dataverse/ping/

# Consulta de cuentas
curl http://127.0.0.1:8000/api/dataverse/accounts/

# Prueba de entidades  
curl http://127.0.0.1:8000/api/dataverse/entities/
```

### Opción 3: Usando Postman o Insomnia
Importa estas URLs como requests GET en tu herramienta preferida.

## Posibles Errores y Soluciones

### Error 401 (Autenticación)
```json
{
    "status": "error",
    "message": "Error de autenticación con Dataverse"
}
```
**Solución**: Verifica que las credenciales en el `.env` son correctas.

### Error 400 (Base URL incorrecta)
**Solución**: Verifica que `DATAVERSE_URL` tiene el formato correcto sin barras finales.

### Error de conexión
**Solución**: Verifica que tienes acceso a internet y que la URL de Dataverse es correcta.

## ¿Qué significa si funciona?

Si al menos el endpoint `/ping/` funciona correctamente, significa que:

✅ **Tu aplicación Python puede autenticarse con Dataverse**  
✅ **Las credenciales son correctas**  
✅ **La conexión está funcionando**  
✅ **Puedes empezar a crear endpoints más complejos**

## Próximos Pasos

Una vez que estos endpoints funcionen, podrás:

1. **Crear endpoints específicos** para tu dominio de negocio
2. **Crear tablas personalizadas** en Dataverse 
3. **Implementar la lógica de bins y lotes** que necesitas
4. **Agregar validaciones y reglas de negocio**