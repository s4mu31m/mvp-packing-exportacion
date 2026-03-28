# Python App

Componente Python del proyecto **MVP Packing Exportación**.

Este módulo concentra el backend Django con la lógica de negocio, modelos de dominio, casos de uso y la capa de integración con Dataverse.

> Referencia completa: [05.1 Backend Python Django — Wiki](https://github.com/s4mu31m/mvp-packing-exportacion/wiki/05.1-%C2%B7-Backend-Python-%E2%80%94-Django)

---

## Estado actual

**Pasos 1, 2 y 3 completados.** El núcleo operacional está implementado, testeado y listo para ser extendido.

| Paso | Estado | Descripción |
|------|--------|-------------|
| Paso 1 — Configuración del proyecto | ✅ Completado | Proyecto Django inicializado, settings por entorno |
| Paso 2 — Modelo de datos local | ✅ Completado | Bin, Lote, Pallet, BinLote, PalletLote, RegistroEtapa |
| Paso 3 — Casos de uso | ✅ Completado | 4 casos de uso implementados y validados con tests |
| Paso 4 — Interfaz operativa (REST + UI) | 🔲 Pendiente | Endpoints funcionales, UI tablet-first |
| Paso 5 — Integración Dataverse | 🔲 Pendiente | Mapping y sync con Dataverse activo |

---

## Responsable principal

**Samuel Montiel**

---

## Estructura actual

```text
python-app/
├── requirements.txt
├── README.md
└── src/
    ├── db.sqlite3
    ├── manage.py
    ├── config/
    │   ├── urls.py
    │   ├── asgi.py
    │   ├── wsgi.py
    │   └── settings/
    │       ├── base.py
    │       ├── local.py
    │       ├── production.py
    │       └── __init__.py
    ├── core/
    │   ├── models.py              # TimeStampedModel, AuditSourceModel (abstractos)
    │   └── dataverse_views.py     # Endpoints de prueba Dataverse
    ├── operaciones/
    │   ├── models.py              # Bin, Lote, Pallet, BinLote, PalletLote, RegistroEtapa
    │   ├── application/
    │   │   ├── use_cases/
    │   │   │   ├── registrar_bin_recibido.py
    │   │   │   ├── crear_lote_recepcion.py
    │   │   │   ├── cerrar_pallet.py
    │   │   │   └── registrar_evento_etapa.py
    │   │   ├── results.py
    │   │   ├── dto.py
    │   │   └── exceptions.py
    │   ├── services/
    │   │   ├── normalizers.py
    │   │   ├── validators.py
    │   │   └── event_builder.py
    │   ├── api/
    │   │   ├── views.py           # Endpoints REST
    │   │   └── serializers.py     # Pendiente de implementar
    │   ├── views.py               # Vistas web (stubs pendientes de conectar)
    │   ├── urls.py
    │   ├── web_urls.py
    │   └── test/
    │       ├── test_registrar_bin_recibido.py
    │       ├── test_crear_lote_recepcion.py
    │       ├── test_cerrar_pallet.py
    │       ├── test_registrar_evento_etapa.py
    │       └── test_flujo_mvp.py
    ├── usuarios/
    │   ├── views.py               # Login, logout, portal
    │   └── templates/usuarios/
    ├── domain/                    # Reservado para capa de dominio
    └── infrastructure/
        └── dataverse/
            ├── auth.py            # DataverseTokenProvider (OAuth2)
            ├── client.py          # DataverseClient (HTTP)
            ├── mapping.py         # Pendiente de implementar
            └── repositories/     # Pendiente de implementar
```

---

## Casos de uso implementados

### `registrar_bin_recibido`
Registra la recepción de un bin preconstruido.
- Valida que el bin no exista para la temporada
- Crea el `Bin` y registra evento `BIN_REGISTRADO` en `RegistroEtapa`

### `crear_lote_recepcion`
Crea un lote agrupando bins.
- Valida que todos los bins existan y no estén ya asignados a otro lote
- Crea el `Lote`, las relaciones `BinLote` y registra evento `LOTE_CREADO`

### `cerrar_pallet`
Consolida lotes en un pallet.
- Opera con `get_or_create` (idempotente)
- Crea `Pallet`, relaciones `PalletLote` y registra eventos `PALLET_CREADO`, `LOTE_ASIGNADO_PALLET`, `PALLET_CERRADO`

### `registrar_evento_etapa`
Registra cualquier evento del flujo operativo.
- Flexible: acepta bin, lote y/o pallet según el tipo de evento
- Soporta 14 tipos de evento (PESAJE, DESVERDIZADO_INGRESO, CONTROL_CALIDAD, etc.)

---

## API REST disponible

| Método | Endpoint | Caso de uso |
|--------|----------|-------------|
| POST | `/api/operaciones/bins/` | `registrar_bin_recibido` |
| POST | `/api/operaciones/lotes/` | `crear_lote_recepcion` |
| POST | `/api/operaciones/pallets/` | `cerrar_pallet` |
| POST | `/api/operaciones/eventos/` | `registrar_evento_etapa` |
| GET | `/api/operaciones/trazabilidad/` | Consulta de RegistroEtapa |

---

## Reglas de negocio implementadas

- Un bin no puede registrarse más de una vez con el mismo código en la misma temporada
- Un lote no puede crearse si alguno de los bins referenciados no existe
- Un bin no puede pertenecer a más de un lote al mismo tiempo
- Un pallet solo se crea si los lotes que lo conforman existen previamente
- Todo evento operacional queda registrado en `RegistroEtapa` para trazabilidad

---

## Ejecución local

### 1. Activar entorno virtual

En Windows:
```bash
.venv\Scripts\activate
```

En Linux / macOS:
```bash
source .venv/bin/activate
```

### 2. Instalar dependencias

```bash
pip install -r requirements.txt
```

### 3. Entrar al proyecto Django

```bash
cd src
```

### 4. Aplicar migraciones

```bash
python manage.py migrate
```

### 5. Levantar servidor local

```bash
python manage.py runserver
```

---

## Verificación técnica

```bash
# Verificar integridad del proyecto
python manage.py check

# Ejecutar suite de tests
python manage.py test operaciones

# Verificar conectividad con Dataverse (requiere .env configurado)
python manage.py dataverse_ping
```

---

## Restricciones técnicas actuales

- Base de datos **SQLite** para desarrollo. No apta para producción con concurrencia — migrar a PostgreSQL antes del piloto.
- Endpoints REST sin autenticación activa — debe resolverse antes de exponer en cualquier entorno compartido.
- Serializers DRF: archivo `api/serializers.py` vacío — respuestas en JSON manual.
- Vistas web (Dashboard, Recepción, Consulta): stubs con datos mock, pendientes de conectar con casos de uso.
- Integración Dataverse: client y auth implementados, `mapping.py` y repositorios pendientes.

---

## Configuración de Dataverse

Variables requeridas en `.env`:

```
DATAVERSE_URL=
DATAVERSE_TENANT_ID=
DATAVERSE_CLIENT_ID=
DATAVERSE_CLIENT_SECRET=
DATAVERSE_API_VERSION=v9.2
DATAVERSE_TIMEOUT=30
```

Ver `SETUP.md` para instrucciones detalladas de configuración.
