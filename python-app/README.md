# Python App

Backend Django del proyecto MVP Packing Exportacion.

## Objetivo del modulo

- Implementar reglas de negocio y trazabilidad operativa.
- Exponer interfaz web (`/operaciones/`) y API (`/api/operaciones/`).
- Ejecutar sobre `sqlite` o `dataverse` mediante la misma capa de repositorios.

## Inicio rapido

### Modo local (SQLite)

```bash
cd python-app
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
cd src
python manage.py migrate
python manage.py runserver
```

### Modo Dataverse

Configura `.env` en `python-app/` con:

```env
PERSISTENCE_BACKEND=dataverse
DATAVERSE_URL=https://<org>.crm.dynamics.com
DATAVERSE_TENANT_ID=<tenant-id>
DATAVERSE_CLIENT_ID=<client-id>
DATAVERSE_CLIENT_SECRET=<client-secret>
DATAVERSE_API_VERSION=v9.2
DATAVERSE_TIMEOUT=30
```

Luego inicia servidor desde `python-app/src`:

```bash
python manage.py runserver
```

## Rutas principales

### API de operaciones (`/api/operaciones/`)

- `POST /bins/`
- `POST /lotes/`
- `POST /pallets/`
- `POST /eventos/`
- `GET /trazabilidad/`

### Diagnostico Dataverse (`/api/dataverse/`)

- `GET /ping/`
- `GET /check_tables/`
- `POST /save_first_bin_code/`
- `GET /get_first_bin_code/`

### Web operativa (`/operaciones/`)

- `recepcion/`
- `desverdizado/`
- `ingreso-packing/`
- `proceso/`
- `control/` (indice)
- `control/desverdizado/`
- `control/packing/`
- `control/camaras/`
- `control/proceso/`
- `paletizado/`
- `camaras/`
- `consulta/` + exportacion CSV/Excel

## Testing

```bash
cd python-app/src
python manage.py check
python manage.py test operaciones
python manage.py test usuarios
```

Pruebas E2E (Playwright):

```bash
cd python-app
python -m pytest tests/e2e/ -v
```

Para validaciones contra Dataverse real, usar:

- [`TESTING_DATAVERSE.md`](TESTING_DATAVERSE.md)
- [`../DATAVERSE_GUIDE.md`](../DATAVERSE_GUIDE.md)

## Estructura

```text
python-app/
|-- README.md
|-- SETUP.md
|-- TESTING_DATAVERSE.md
|-- requirements.txt
`-- src/
    |-- config/
    |-- core/
    |-- domain/
    |-- infrastructure/
    |-- operaciones/
    `-- usuarios/
```

## Referencia funcional y de arquitectura

Documentacion canónica: <https://github.com/s4mu31m/mvp-packing-exportacion/wiki>
