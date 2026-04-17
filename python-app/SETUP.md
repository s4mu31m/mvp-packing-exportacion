# Setup de Desarrollo

Guia de configuracion local para ejecutar el backend Django.

## 1) Preparar Python y dependencias

Desde `python-app/`:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 2) Configurar variables de entorno

Crear archivo `python-app/.env` con estos valores minimos:

```env
PERSISTENCE_BACKEND=sqlite
DATAVERSE_URL=https://<org>.crm.dynamics.com
DATAVERSE_TENANT_ID=<tenant-id>
DATAVERSE_CLIENT_ID=<client-id>
DATAVERSE_CLIENT_SECRET=<client-secret>
DATAVERSE_API_VERSION=v9.2
DATAVERSE_TIMEOUT=30
```

Notas:

- usa `PERSISTENCE_BACKEND=sqlite` para desarrollo local sin dependencia externa;
- cambia a `PERSISTENCE_BACKEND=dataverse` cuando quieras probar integracion real.

## 3) Migrar base local

```bash
cd src
python manage.py migrate
```

## 4) Levantar servidor

```bash
python manage.py runserver
```

## 5) Verificaciones basicas

- Login: <http://127.0.0.1:8000/usuarios/login/>
- Dashboard: <http://127.0.0.1:8000/operaciones/>
- Ping Dataverse: <http://127.0.0.1:8000/api/dataverse/ping/>
- Check tables Dataverse: <http://127.0.0.1:8000/api/dataverse/check_tables/>

## Seguridad

- no commitear `python-app/.env`;
- compartir secretos solo por canales seguros;
- rotar secretos comprometidos inmediatamente.
