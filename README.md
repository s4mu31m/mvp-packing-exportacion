# MVP Packing Exportación

Repositorio principal del proyecto **MVP Packing Exportación**, orientado a la digitalización operativa del módulo de **packing y exportación**.

> **Documentación centralizada:** La [wiki del proyecto](https://github.com/s4mu31m/mvp-packing-exportacion/wiki) es el centro de conocimiento del MVP. Este repositorio es la materialización técnica; la wiki consolida y explica.

---

## Propósito

Establecer una base ordenada para levantar requerimientos, definir alcance, documentar la arquitectura y construir una primera solución funcional orientada al uso en terreno.

---

## Estado actual

El proyecto completó los tres primeros pasos del MVP:

| Paso | Estado | Descripción |
|------|--------|-------------|
| Paso 1 — Configuración del proyecto | ✅ Completado | Proyecto Django inicializado, estructura base definida |
| Paso 2 — Modelo de datos local en Django | ✅ Completado | Entidades Bin, Lote, Pallet, BinLote, PalletLote, RegistroEtapa implementadas |
| Paso 3 — Lógica de negocio por casos de uso | ✅ Completado | Capa de aplicación con casos de uso implementados y validados con tests |
| Paso 4 — Interfaz operativa mínima (REST) | 🔲 Pendiente | Exposición de casos de uso vía endpoints |
| Paso 5 — Integración con Dataverse | 🔲 Pendiente | Sincronización con Dataverse como base estructural de datos |

---

## Eje funcional principal

```
Bin → Lote → Etapa → Pallet
```

Los bins llegan **preconstruidos** desde el módulo previo. Este módulo recibe, valida, relaciona y traza.

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
│   ├── README.md
│   ├── requirements.txt
│   └── src/
│       ├── manage.py
│       ├── config/
│       ├── core/
│       ├── operaciones/
│       ├── usuarios/
│       ├── domain/
│       └── infrastructure/
└── README.md
```

---

## Descripción de carpetas

### `.github/`
Plantillas de issues y pull requests para gestión colaborativa del repositorio.

### `docs/`
Documentación funcional y técnica del proyecto, organizada por dominio:

- **actas/**: minutas y acuerdos de reuniones.
- **alcance/**: definición del alcance funcional del MVP.
- **arquitectura/**: decisiones y lineamientos de arquitectura.
- **levantamiento/**: flujo operativo, actores y hallazgos del levantamiento.
- **planning/**: roadmap, estado de avance y planificación.

### `power-platform/`
Espacio reservado para documentar la línea de trabajo asociada a Microsoft Power Platform y Dataverse.

### `python-app/`
Módulo backend en Python/Django. Contiene la lógica de negocio, modelos de dominio, casos de uso, servicios y la capa de integración con Dataverse.

---

## Tecnologías

- **Python + Django** — backend, lógica de negocio, casos de uso
- **Django REST Framework** — exposición de API REST
- **Microsoft Dataverse / Power Platform** — base estructural de datos (integración preparada, pendiente de activar)
- **SQLite** — base de datos local para desarrollo
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
