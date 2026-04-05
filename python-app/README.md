# Python App

Componente Python del proyecto **MVP Packing Exportación**.

Backend Django con lógica de negocio, modelos de dominio, casos de uso y capa de integración con Dataverse (Microsoft Power Platform).

> Referencia completa: [05.1 Backend Python Django — Wiki](https://github.com/s4mu31m/mvp-packing-exportacion/wiki/05.1-%C2%B7-Backend-Python-%E2%80%94-Django)

---

## Estado actual (2026-04-04)

El backend Dataverse está implementado para todas las entidades del flujo. Las vistas web son compatibles con ambos backends.

| Componente | SQLite | Dataverse |
|---|---|---|
| Recepción de bins (flujo lote abierto) | Funcional | Funcional |
| Pesaje / conformación de lote | Funcional | Funcional |
| Dashboard con KPIs | Funcional | Funcional (con limitaciones de estado, ver abajo) |
| Cámara de mantención | Funcional | Funcional |
| Desverdizado | Funcional | Funcional |
| Calidad desverdizado | Funcional | Funcional |
| Ingreso a packing | Funcional | Funcional |
| Registro packing | Funcional | Funcional |
| Control proceso packing | Funcional | Funcional |
| Calidad pallet | Funcional | Funcional |
| CalidadPalletMuestra | Funcional | Funcional (tabla `crf21_calidad_pallet_muestras` creada 2026-04-04) |
| Cámara de frío | Funcional | Funcional |
| Medición temperatura salida | Funcional | Funcional |
| Trazabilidad (registro_etapas) | Funcional | No-op con log local (tabla no existe en Dataverse) |
| Control de acceso por rol (3 niveles) | Funcional | Funcional (autenticación local Django, ambos backends) |

---

## Cómo probar localmente en SQLite

```bash
cd src
# Asegurarse que .env tiene PERSISTENCE_BACKEND=sqlite (o sin esa variable)
python manage.py migrate
python manage.py runserver
```

Acceder en `http://localhost:8000/`.

---

## Cómo probar con Dataverse

1. Configurar `.env` con las credenciales Dataverse:

```
PERSISTENCE_BACKEND=dataverse
DATAVERSE_URL=https://<org>.crm2.dynamics.com
DATAVERSE_TENANT_ID=<tenant-id>
DATAVERSE_CLIENT_ID=<client-id>
DATAVERSE_CLIENT_SECRET=<secret>
DATAVERSE_API_VERSION=v9.2
DATAVERSE_TIMEOUT=30
```

2. Verificar conectividad:

```bash
cd src
# Ping Dataverse
curl http://localhost:8000/api/dataverse/ping/

# Verificar tablas (requiere servidor corriendo)
curl http://localhost:8000/api/dataverse/check_tables/
```

3. Levantar servidor:

```bash
python manage.py runserver
```

Las vistas de recepción, dashboard y todas las etapas operacionales escriben
y leen desde Dataverse. Los tests de Django siguen corriendo contra SQLite
(no requieren Dataverse activo).

---

## Diferencias entre backends SQLite y Dataverse

| Concepto | SQLite | Dataverse |
|---|---|---|
| `temporada` | Campo explícito en modelos | No existe; se filtra por fechas o se ignora |
| `estado` del lote | Persiste (abierto/cerrado/finalizado) | No persiste; siempre retorna `"abierto"` |
| `temporada_codigo`, `correlativo_temporada` | Persisten | No persisten; retornan `""` y `None` |
| Dashboard: lotes cerrados/finalizados | Contador real | Siempre 0 (estado no trackeable) |
| Trazabilidad de etapas | `RegistroEtapa` en SQLite | Log local (no persiste en Dataverse) |
| Correlativos de código | SequenceCounter atómico | Conteo de registros existentes (no atómico) |
| Transacciones | ACID via Django ORM | No soportado por Dataverse Web API |
| `CalidadPalletMuestra` | ORM directo | `DataverseCalidadPalletMuestraRepository` via OData |

> Ver tabla completa de límites aceptados en `DATAVERSE_GUIDE.md §17` y en `docs/cierre-mvp/limites-aceptados-mvp.md`.

---

## Selección de backend

```python
# config/settings/base.py o .env
PERSISTENCE_BACKEND = "sqlite"      # desarrollo local (default)
PERSISTENCE_BACKEND = "dataverse"   # producción / pruebas reales
```

---

## Tests

```bash
cd src
python manage.py check
python manage.py test operaciones   # 204 tests — OK
python manage.py test usuarios      # 43 tests — 1 error pre-existente no bloqueante
```

Los tests corren siempre en SQLite. Para smoke tests contra Dataverse real,
usar el shell de Django con `PERSISTENCE_BACKEND=dataverse` en `.env`
o los scripts de diagnóstico en `scripts/dataverse/`.

Incluye evidencia automatizada de:
- Flujo completo: login → recepción → cierre de lote → todas las etapas → consulta/exportación
- Tests negativos de permisos por módulo (rol incorrecto → 403) y admin bypass

---

## Estructura principal

```text
python-app/
├── .env                       # Variables de entorno (no commitear)
├── requirements.txt
├── README.md
├── TECHNICAL_CHANGES.md       # Historial técnico detallado
└── src/
    ├── config/settings/       # base.py, local.py, production.py
    ├── core/
    │   └── dataverse_views.py # Endpoints ping/check_tables
    ├── domain/
    │   └── repositories/base.py  # Contratos de repositorio (ABCs + records)
    ├── infrastructure/
    │   ├── repository_factory.py # Selector sqlite|dataverse
    │   ├── sqlite/repositories.py
    │   └── dataverse/
    │       ├── auth.py        # OAuth2 client credentials
    │       ├── client.py      # OData HTTP client
    │       ├── mapping.py     # Schema real Dataverse (prefijo crf21_*)
    │       └── repositories/__init__.py  # Implementaciones Dataverse
    └── operaciones/
        ├── models.py
        ├── views.py
        ├── forms.py
        ├── application/use_cases/  # 18 casos de uso
        ├── services/
        └── test/                   # 196 tests
```

---

## Responsable principal

**Samuel Montiel**
