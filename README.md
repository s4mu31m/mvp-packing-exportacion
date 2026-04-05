# MVP Packing Exportación

Repositorio principal del proyecto **MVP Packing Exportación**, orientado a la digitalización operativa del módulo de **packing y exportación**.

> **Documentación centralizada:** La [wiki del proyecto](https://github.com/s4mu31m/mvp-packing-exportacion/wiki) es el centro de conocimiento del MVP. Este repositorio es la materialización técnica; la wiki consolida y explica.

---

## Propósito

Digitalizar el flujo operativo de recepción, trazabilidad y packing de fruta en planta, reemplazando registros manuales por un sistema web que centraliza la información en Dataverse (Microsoft Power Platform).

---

## Estado actual — 2026-04-04

| Paso | Estado | Descripción |
|------|--------|-------------|
| Paso 1 — Configuración del proyecto | ✅ Completado | Proyecto Django inicializado, estructura base definida |
| Paso 2 — Modelo de datos local | ✅ Completado | Entidades Bin, Lote, Pallet, BinLote, PalletLote, RegistroEtapa, SequenceCounter implementadas |
| Paso 3 — Lógica de negocio (casos de uso) | ✅ Completado | Capa de aplicación con casos de uso, validados con tests |
| Paso 4 — Interfaz operativa web | ✅ Completado | Vistas HTML operativas para cada etapa del flujo |
| Paso 4b — API REST | ✅ Completado | Endpoints DRF expuestos para bins, lotes, pallets, eventos y trazabilidad |
| Paso 5 — Integración con Dataverse | ✅ Completado | Capa de repositorios Dataverse implementada para todas las entidades del flujo; vistas web compatibles con ambos backends; límites conocidos documentados en `docs/cierre-mvp/` |

---

## Flujo operativo cubierto

```
Recepción → Desverdizado → Ingreso Packing → Proceso → Control → Paletizado → Cámaras
```

Cada etapa tiene su propia vista web. La recepción implementa el flujo completo: apertura de lote, registro de bins con código generado automáticamente y cierre de lote con pesaje (kg bruto/neto).

> **Nota backend:** En SQLite el avance del lote se representa con el campo `estado` (abierto/cerrado/finalizado). En Dataverse se usa el campo `crf21_etapa_actual` (Recepcion, Pesaje, Desverdizado, …) como fuente de verdad operativa.

---

## Generación automática de códigos

Los códigos operacionales **nunca se digitan manualmente**. El backend los construye a partir de los atributos base capturados en el frontend:

| Entidad | Formato | Ejemplo |
|---------|---------|---------|
| Bin | `{productor}-{cultivo}-{variedad}-{cuartel}-{DDMMYY}-{correlativo:03d}` | `AG01-LM-Eur-C05-120326-001` |
| Lote (LotePlanta) | `LP-{temporada}-{correlativo:06d}` | `LP-2025-2026-000001` |
| Pallet | `PA-{YYYYMMDD}-{correlativo:04d}` | `PA-20260329-0012` |

Los correlativos se gestionan mediante `SequenceCounter` con `select_for_update()` para garantizar unicidad bajo concurrencia.

---

## Estructura del repositorio

```text
mvp-packing-exportacion/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── blocker.md
│   │   └── tarea.md
│   └── PULL_REQUEST_TEMPLATE.md
├── docs/
│   ├── actas/
│   ├── alcance/
│   ├── arquitectura/
│   ├── levantamiento/
│   └── planning/
├── power-platform/
├── python-app/
│   ├── requirements.txt
│   └── src/
│       ├── manage.py
│       ├── config/              # Settings, URLs raíz, WSGI/ASGI
│       ├── core/                # Modelos base, context processors, endpoints Dataverse
│       ├── operaciones/
│       │   ├── models.py        # Bin, Lote, Pallet, BinLote, PalletLote, RegistroEtapa, SequenceCounter
│       │   ├── application/     # Casos de uso, DTOs, resultados, excepciones
│       │   ├── api/             # Serializers y vistas DRF (REST)
│       │   ├── services/        # Generadores de código, secuencias, validadores, temporada
│       │   ├── templates/       # Vistas HTML por etapa operativa
│       │   ├── urls.py          # Rutas API REST
│       │   └── web_urls.py      # Rutas vistas web
│       ├── usuarios/            # Autenticación y portal de acceso
│       ├── domain/              # Interfaces de repositorios (abstracciones)
│       └── infrastructure/
│           ├── dataverse/       # Cliente OData, autenticación, mapping de campos
│           └── sqlite/          # Implementación de repositorios en SQLite
└── README.md
```

---

## API REST (`/api/operaciones/`)

| Método | Endpoint | Caso de uso |
|--------|----------|-------------|
| POST | `/api/operaciones/bins/` | Registrar bin recibido |
| POST | `/api/operaciones/lotes/` | Crear lote de recepción |
| POST | `/api/operaciones/pallets/` | Cerrar pallet |
| GET | `/api/operaciones/trazabilidad/` | Consulta de trazabilidad |
| POST | `/api/operaciones/eventos/` | Registrar evento de etapa |

## Vistas web (`/operaciones/`)

| Ruta | Vista |
|------|-------|
| `/operaciones/` | Dashboard |
| `/operaciones/recepcion/` | Recepción de bins, apertura y cierre de lote (incluye pesaje) |
| `/operaciones/desverdizado/` | Ingreso/salida de desverdizado |
| `/operaciones/ingreso-packing/` | Ingreso a proceso de packing |
| `/operaciones/proceso/` | Proceso de packing |
| `/operaciones/control/` | Control de calidad |
| `/operaciones/paletizado/` | Paletizado |
| `/operaciones/camaras/` | Cámaras de frío y mantención |
| `/operaciones/consulta/` | Consulta de jefatura |
| `/operaciones/consulta/exportar/` | Exportación CSV de lotes |

> El pesaje del lote (kg bruto/neto de conformación) se captura en el formulario de cierre del lote dentro de Recepción. No existe una vista operativa separada `/operaciones/pesaje/`.

## Diagnóstico Dataverse (`/api/dataverse/`)

| Endpoint | Descripción |
|----------|-------------|
| `/api/dataverse/ping/` | Verifica conectividad con Dataverse |
| `/api/dataverse/check_tables/` | Lista tablas disponibles |
| `/api/dataverse/save_first_bin_code/` | Escribe un registro de prueba |
| `/api/dataverse/get_first_bin_code/` | Lee el registro de prueba |

---

## Tecnologías

- **Python + Django** — backend, lógica de negocio, casos de uso
- **Django REST Framework** — API REST
- **Microsoft Dataverse / Power Platform** — backend de producción; capa de repositorios completa; vistas web compatibles con ambos backends
- **SQLite** — base de datos local de desarrollo
- **GitHub** — gestión del proyecto

---

## Gestión del proyecto

El trabajo se organiza en GitHub mediante:

- **Issues** para tareas y bloqueos.
- **Pull Request Template** para estandarizar revisiones.
- **Wiki** como centro de conocimiento del proyecto.
- **Documentación por dominio** dentro de `docs/`.

---

**Wiki del proyecto:** https://github.com/s4mu31m/mvp-packing-exportacion/wiki
