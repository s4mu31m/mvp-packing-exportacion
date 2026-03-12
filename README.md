# MVP Packing Exportación

Repositorio principal del proyecto **MVP Packing Exportación**, orientado a la digitalización operativa del módulo de **packing y exportación**.

Este repositorio concentra la **documentación base**, la **organización del trabajo en GitHub** y dos líneas iniciales de implementación:

- **Python**, para el desarrollo técnico de la aplicación.
- **Power Platform**, para la exploración y documentación de la línea low-code.

## Propósito

El objetivo de este MVP es establecer una base ordenada para levantar requerimientos, definir alcance, documentar la arquitectura inicial y coordinar el desarrollo de una primera solución funcional.

## Estado actual

El proyecto se encuentra en una etapa inicial de **estructuración y documentación**, con una base de gestión ya creada en GitHub y un entorno de trabajo en Python ya levantado.

## Estructura actual del repositorio

```text
mvp-packing-exportacion/
├── .github/
│   ├── ISSUE_TEMPLATE/
│   │   ├── blocker.md
│   │   └── tarea.md
│   └── PULL_REQUEST_TEMPLATE.md
├── docs/
│   ├── actas/
│   │   └── README.md
│   ├── alcance/
│   │   └── README.md
│   ├── arquitectura/
│   │   └── README.md
│   ├── levantamiento/
│   │   └── README.md
│   └── planning/
│       └── README.md
├── power-platform/
│   └── README.md
├── python-app/
│   ├── README.md
│   ├── requirements.txt
│   └── .venv/
└── README.md
```

## Descripción de carpetas

### `.github/`
Contiene la base de gestión colaborativa del repositorio, incluyendo plantillas para issues y pull requests.

### `docs/`
Agrupa la documentación principal del proyecto, organizada por tema:

- **actas**: registro de acuerdos o sesiones de trabajo.
- **alcance**: definición del alcance funcional del MVP.
- **arquitectura**: lineamientos y decisiones de arquitectura.
- **levantamiento**: recopilación inicial de necesidades, procesos o requerimientos.
- **planning**: planificación general del trabajo.

### `power-platform/`
Espacio reservado para documentar y desarrollar la línea de trabajo asociada a Microsoft Power Platform.

### `python-app/`
Contiene la base técnica de la aplicación en Python, incluyendo el archivo de dependencias y un entorno virtual local de desarrollo.

> Se recomienda no versionar `.venv/` en el repositorio remoto, ya que corresponde a un entorno local.

## Gestión del proyecto

La organización del trabajo se apoya en GitHub mediante:

- **Issues** para tareas y bloqueos.
- **Pull Request Template** para estandarizar revisiones.
- **Documentación por dominio** dentro de `docs/`.

## Próximos pasos sugeridos

- completar el contenido de cada `README.md` dentro de `docs/`,
- definir la arquitectura inicial del MVP,
- formalizar el backlog técnico y funcional,
- comenzar la implementación de la primera versión operativa.

## Tecnologías consideradas

- **Python**
- **Microsoft Power Platform**
- **GitHub**

---

**Estado del repositorio:** en construcción  
**Enfoque:** documentación, organización y desarrollo inicial del MVP
