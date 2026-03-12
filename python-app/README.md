# Python App

Componente Python del proyecto **MVP Packing Exportación**.

Este módulo concentra la base del desarrollo backend sobre **Django**, junto con una organización inicial orientada a separar configuración, aplicaciones del proyecto, dominio e integración con servicios externos. Su objetivo es servir como base técnica para la construcción del MVP y para la evolución posterior del sistema.

## Estado actual

Actualmente `python-app` ya no es solo un espacio reservado: cuenta con una base funcional de proyecto Django, entorno local de desarrollo, dependencias definidas y una estructura inicial para crecer de forma ordenada.

A la fecha, este componente incluye:

- entorno virtual local en `.venv`
- archivo `requirements.txt` para dependencias del proyecto
- proyecto Django inicializado dentro de `src`
- base de datos local `db.sqlite3` para desarrollo
- archivo `manage.py` para la administración del proyecto
- configuración desacoplada por ambiente en `config/settings`
- apps iniciales del sistema: `core`, `operaciones` y `usuarios`
- estructura de dominio separada en `domain`
- base de integración externa en `infrastructure/dataverse`

## Responsable principal

**Samuel Montiel**

## Propósito del módulo

Este componente está pensado para cubrir el desarrollo técnico del backend y de la lógica del MVP, incluyendo:

- lógica de negocio del proceso operativo
- modelado y persistencia de datos
- vistas, formularios o endpoints según la arquitectura definida
- organización del dominio del sistema
- integración con servicios o fuentes externas
- soporte a procesos complementarios de Power Platform cuando corresponda

## Estructura actual resumida

```text
python-app/
├── .venv/
├── requirements.txt
├── README.md
└── src/
    ├── db.sqlite3
    ├── manage.py
    ├── config/
    │   ├── asgi.py
    │   ├── urls.py
    │   ├── wsgi.py
    │   └── settings/
    │       ├── base.py
    │       ├── local.py
    │       ├── production.py
    │       └── __init__.py
    ├── core/
    ├── operaciones/
    ├── usuarios/
    ├── domain/
    │   ├── entities/
    │   ├── repositories/
    │   └── services/
    └── infrastructure/
        └── dataverse/
            ├── auth.py
            ├── client.py
            ├── mapping.py
            └── repositories/
```

## Descripción de la estructura

### `src/`
Contiene el código fuente principal del módulo Python y el proyecto Django activo.

### `config/`
Agrupa la configuración global del proyecto Django.

- `urls.py`: enrutamiento principal
- `asgi.py` y `wsgi.py`: puntos de entrada para despliegue
- `settings/`: separación de configuración por entorno

### `config/settings/`
La configuración está organizada por archivos, lo que facilita escalar el proyecto y separar responsabilidades:

- `base.py`: configuración común del proyecto
- `local.py`: configuración de desarrollo local
- `production.py`: configuración prevista para despliegue

### `core/`
App base del proyecto. Sirve como punto de partida para componentes transversales o funcionalidades comunes del sistema.

### `operaciones/`
App destinada al dominio operativo del MVP. Por su nombre y ubicación, está alineada con la futura lógica del módulo de packing y exportación.

### `usuarios/`
App destinada a encapsular la gestión o lógica relacionada con usuarios dentro del sistema.

### `domain/`
Estructura orientada a separar reglas de negocio del framework.

- `entities/`: entidades del dominio
- `repositories/`: contratos o abstracciones de acceso a datos
- `services/`: servicios de negocio

### `infrastructure/dataverse/`
Base inicial para integración con Dataverse u otra capa externa similar.

- `auth.py`: autenticación
- `client.py`: cliente de conexión
- `mapping.py`: transformación o mapeo de datos
- `repositories/`: implementación de repositorios de infraestructura

## Ejecución local

### 1. Activar entorno virtual

En Windows:

```bash
.venv\Scripts\activate
```

En Linux o macOS:

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

## Restricciones técnicas actuales

En el estado actual del módulo, existen restricciones y supuestos técnicos que deben considerarse durante el desarrollo:

- la aplicación está preparada principalmente para **desarrollo local**, no como entorno productivo cerrado
- la persistencia actualmente visible corresponde a **`db.sqlite3`**, por lo que la base de datos definitiva aún debe confirmarse según la arquitectura final del MVP
- la configuración está separada en `base.py`, `local.py` y `production.py`, pero la estrategia final de variables sensibles, secretos y despliegue seguro todavía debe formalizarse
- la integración con **Dataverse** existe como base técnica inicial, pero aún debe validarse su alcance real dentro del flujo definitivo del proyecto
- la estructura de **dominio** e **infraestructura** ya está iniciada, aunque sus contratos, repositorios y casos de uso todavía están en fase de construcción
- el entorno virtual `.venv`, los archivos compilados y carpetas como `__pycache__` corresponden a artefactos locales de desarrollo y no deben considerarse parte del entregable funcional
- el módulo mantiene una arquitectura abierta para convivir con `power-platform`, por lo que algunas responsabilidades del sistema todavía dependen de decisiones funcionales y técnicas del proyecto general

## Consideraciones de desarrollo

- `.venv` corresponde al entorno local y no debería versionarse como parte del código del proyecto
- `__pycache__` y archivos compilados de Python tampoco deberían formar parte del repositorio
- `db.sqlite3` puede servir para desarrollo inicial, pero la persistencia definitiva dependerá de la arquitectura acordada para el MVP
- la separación entre `domain` e `infrastructure` deja una base útil para evitar que toda la lógica quede acoplada directamente a Django

## Próximos avances sugeridos

- definir modelos de negocio en las apps del proyecto
- conectar entidades del dominio con repositorios reales
- implementar casos de uso del módulo de operaciones
- formalizar integración con Dataverse si será parte del flujo definitivo
- documentar endpoints, flujos y decisiones de arquitectura
- preparar configuración segura para entorno productivo

## Relación con el proyecto general

`python-app` es uno de los componentes del repositorio principal del MVP, junto con la documentación funcional en `docs/` y el módulo `power-platform/`. Su rol es aportar la base backend y técnica para las piezas que requieran una implementación más controlada, extensible y mantenible dentro de la solución.
