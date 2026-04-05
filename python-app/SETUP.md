# Configuración del Entorno de Desarrollo

## Para trabajar con este proyecto:

### 1. Configurar credenciales de Dataverse

#### IMPORTANTE: La aplicación Azure ya está configurada

La aplicación **"MVP-Packing-Backend"** ya está registrada en Azure AD y configurada en Power Platform. **NO necesitas crear una nueva aplicación**.

#### A. Obtener credenciales de la aplicación existente

1. Ve al **Azure Portal** (portal.azure.com)
2. Navega a **Azure Active Directory** > **App registrations**  
3. **Busca y selecciona** la aplicación existente: **"MVP-Packing-Backend"**
4. En la página **Overview**, copia:
   - **Application (client) ID**
   - **Directory (tenant) ID**
5. Ve a **Certificates & secrets**
6. Si hay un client secret existente, úsalo. Si no o ha expirado:
   - Haz clic en **"New client secret"**
   - Anota el **Client secret** (¡guárdalo inmediatamente!)

#### B. Verificar configuración en Power Platform (Opcional)

La aplicación ya debería estar configurada, pero puedes verificar:
1. Ve al **Power Platform Admin Center** (admin.powerplatform.microsoft.com)
2. **Environments** > Tu entorno > **Users + permissions** > **Application users**
3. Verifica que **"MVP-Packing-Backend"** aparece en la lista con roles asignados

#### C. Configurar archivo .env

1. Copia el archivo `.env.example` como `.env`:
   ```bash
   cp .env.example .env
   ```

2. Obtén la **DATAVERSE_URL** del Power Platform Admin Center:
   - Environments > Tu entorno > **Environment URL**
   - Formato: `https://[tu-org].api.crm.dynamics.com`

3. Completa el archivo `.env` con las credenciales obtenidas:
   - `DATAVERSE_URL`: URL del entorno Dataverse
   - `DATAVERSE_TENANT_ID`: Directory (tenant) ID de la app MVP-Packing-Backend
   - `DATAVERSE_CLIENT_ID`: Application (client) ID de la app MVP-Packing-Backend  
   - `DATAVERSE_CLIENT_SECRET`: Client secret de la app MVP-Packing-Backend

**Nota:** Si otro desarrollador ya configuró y tienes las credenciales funcionando, puedes usar las mismas en lugar de buscarlas en Azure.
   
### 2. Configurar entorno Python

1. Crear entorno virtual:
   ```bash
   python -m venv .venv
   ```

2. Activar entorno:
   ```bash
   # Windows
   .venv\Scripts\activate
   
   # Linux/Mac
   source .venv/bin/activate
   ```

3. Instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```

### 3. Configurar base de datos

```bash
cd src
python manage.py migrate
```

### 4. Ejecutar servidor

```bash
python manage.py runserver
```

### 5. Probar conectividad

Visita estos endpoints para verificar que la conexión funciona:
- http://127.0.0.1:8000/api/dataverse/ping/
- http://127.0.0.1:8000/api/dataverse/check_tables/
- http://127.0.0.1:8000/api/dataverse/save_first_bin_code/  (POST)
- http://127.0.0.1:8000/api/dataverse/get_first_bin_code/

Las vistas operativas (`/operaciones/...`) requieren autenticación.
Usa http://127.0.0.1:8000/usuarios/login/ para iniciar sesión antes de acceder a ellas.

## Notas de Seguridad

- **NUNCA** subas el archivo `.env` al repositorio
- Las credenciales deben compartirse por canales seguros (Teams, email corporativo, etc.)
- El archivo `.env` está en `.gitignore` para protección automática