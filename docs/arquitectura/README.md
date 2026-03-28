# Arquitectura del sistema

> Referencia completa: [04 Arquitectura de la solución — Wiki](https://github.com/s4mu31m/mvp-packing-exportacion/wiki/04-Arquitectura-de-la-solucion)

---

## Objetivo

Documentar la arquitectura base del MVP y la separación lógica de responsabilidades entre los componentes del sistema.

---

## Responsabilidades por componente

| Componente | Rol en la arquitectura |
|---|---|
| **Dataverse** | Base estructural principal de datos del MVP. Solicitado por el cliente para mantener consistencia con sus otros módulos. Es donde viven las tablas, columnas, relaciones y la estructura de datos objetivo. |
| **Django/Python** | Framework de desarrollo del módulo de exportación. Capa de lógica, validaciones, cálculos e inserción de datos. Motor de ejecución del módulo. No es el sistema rector de datos. |
| **Wiki** | Centro de conocimiento centralizado. Consolida y explica. No reemplaza al contrato funcional ni al repositorio ni a Dataverse. |
| **Repositorio** | Espacio de trabajo donde se materializa técnicamente el proyecto. Fuente primaria de la implementación en código. |

---

## Vista general de la arquitectura

```
UI tablet-first / navegador
    ↓ HTTPS
Backend Python — Django
    ↓ OAuth2 client credentials
Microsoft Entra ID
    ↓ Access token
Dataverse
    ↓
Tablas del MVP: Bin / LotePlanta / Pallet / ...
```

---

## Capas principales

- **Configuración:** Settings del proyecto Django separados por entorno (`base.py`, `local.py`, `production.py`).

- **Aplicación:** Apps Django (`core`, `operaciones`, `usuarios`) con la capa de lógica de negocio centralizada en `operaciones/application/use_cases/`.

- **Dominio:** Entidades, servicios y contratos del negocio. Carpeta `domain/` reservada para esta capa.

- **Infraestructura:** Integraciones técnicas, autenticación, clientes y repositorios externos. Capa `infrastructure/dataverse/` como frontera de integración con Dataverse.

---

## Arquitectura interna de la app `operaciones`

```
operaciones/
├── models.py                         # Modelos de dominio (ORM Django)
├── application/
│   ├── use_cases/                    # Casos de uso: orquestación de la lógica de negocio
│   │   ├── registrar_bin_recibido.py
│   │   ├── crear_lote_recepcion.py
│   │   ├── cerrar_pallet.py
│   │   └── registrar_evento_etapa.py
│   ├── results.py                    # Objetos de resultado estandarizados
│   ├── dto.py                        # Data Transfer Objects
│   └── exceptions.py                 # Excepciones de dominio
├── services/
│   ├── normalizers.py                # Normalización de datos de entrada
│   ├── validators.py                 # Validaciones de negocio reutilizables
│   └── event_builder.py              # Construcción de registros de etapa
└── api/
    ├── views.py                      # Endpoints REST
    └── serializers.py                # Serializers (pendiente de implementar)
```

**Principio rector:** la lógica de negocio no reside en las vistas. Las vistas solo reciben la solicitud y delegan al caso de uso correspondiente.

---

## Criterios arquitectónicos

1. **Separación entre configuración, negocio e integración** — no deben quedar mezclados.
2. **Crecimiento modular por componentes** — cada funcionalidad en un módulo con responsabilidades claras.
3. **Múltiples entornos sin cambios al código** — controlado via settings y variables de entorno.
4. **Integraciones encapsuladas** — todo acceso a Dataverse concentrado en `infrastructure/dataverse/`.
5. **Lógica de negocio centralizada fuera de vistas** — los casos de uso son reutilizables desde cualquier punto de entrada.

---

## Estado actual de la arquitectura

| Aspecto | Estado |
|---|---|
| Estructura del proyecto Django | ✅ Implementada |
| Modelo de datos local (Bin, Lote, Pallet, BinLote, PalletLote, RegistroEtapa) | ✅ Implementado — Paso 2 |
| Casos de uso (registrar_bin_recibido, crear_lote_recepcion, cerrar_pallet, registrar_evento_etapa) | ✅ Implementados y testeados — Paso 3 |
| API REST básica (5 endpoints) | ✅ Implementada |
| Preparación para integración Dataverse (client, auth, estructura) | ✅ Preparada, no activa en ambiente real |
| Autenticación con Entra ID / credenciales reales | 🔲 Pendiente — depende de accesos del cliente |
| Integración activa con Dataverse (mapping, sync) | 🔲 Pendiente — etapa posterior |
| UI funcional tablet-first | 🔲 Pendiente |

---

## Preparación para integración Dataverse

Se formalizó una preparación técnica del backend sin depender todavía de accesos productivos:

- Separación explícita de settings por entorno.
- Capa `infrastructure/dataverse/` como frontera de integración externa.
- Campo `dataverse_id` nullable en entidades maestras para preparación sin migraciones adicionales.
- `DataverseTokenProvider` (OAuth2) y `DataverseClient` (HTTP) implementados y funcionales.

**Alcance real:** este avance deja preparada la estructura, pero no constituye una conexión operativa. La conexión efectiva sigue dependiendo de accesos, credenciales y validación del ambiente del cliente.

---

## Restricciones técnicas actuales

- Base de datos: **SQLite** para desarrollo local (no apta para producción con concurrencia).
- Autenticación API: sin autenticación activa en endpoints — debe resolverse antes del piloto.
- Serializers DRF: archivo vacío — respuestas manuales en JSON.
- Vistas web (Dashboard, Recepción, Consulta): stubs con datos mock, pendientes de conectar con casos de uso.

---

## Documentos relacionados

- `docs/arquitectura/reestructura-planificaion.md` — documento de planificación v2 (referencia histórica).
- [04 Arquitectura — Wiki](https://github.com/s4mu31m/mvp-packing-exportacion/wiki/04-Arquitectura-de-la-solucion)
- [05.1 Backend Python Django — Wiki](https://github.com/s4mu31m/mvp-packing-exportacion/wiki/05.1-%C2%B7-Backend-Python-%E2%80%94-Django)
