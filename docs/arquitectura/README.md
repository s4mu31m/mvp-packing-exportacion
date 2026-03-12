# Arquitectura

## Objetivo

Documentar la arquitectura base del módulo Python del proyecto **MVP Packing Exportación**, dejando registro de la estructura inicial, la separación lógica de componentes y los criterios técnicos mínimos que guiarán la implementación del sistema.

## Estado actual de la arquitectura

Actualmente el proyecto cuenta con una base inicial de arquitectura para el desarrollo en Python, organizada sobre Django y preparada para crecer de forma modular.

El módulo `python-app` ya dispone de:

- entorno local de desarrollo en Python
- archivo `requirements.txt` para dependencias
- proyecto Django inicializado en `src/`
- archivo `manage.py`
- configuración separada por entornos en `config/settings`
- apps base del proyecto
- capas iniciales para dominio e integración externa

Esta base permite iniciar el desarrollo del MVP con una estructura ordenada, evitando mezclar configuración, lógica de negocio e integración técnica desde las primeras iteraciones.

## Estructura general registrada

La arquitectura actual se organiza en dos niveles:

### 1. Documentación del proyecto

La carpeta `docs/` concentra la documentación funcional y técnica del repositorio:

- `actas/`
- `alcance/`
- `arquitectura/`
- `levantamiento/`
- `planning/`

La carpeta `docs/arquitectura/` tiene como propósito registrar decisiones técnicas, estructura general del sistema, lineamientos de integración y evolución de la solución.

### 2. Módulo Python

El desarrollo técnico del framework Python se encuentra en `python-app/`, con una estructura base orientada a backend modular.

## Componentes principales definidos

### Configuración del proyecto

Dentro de `src/config/` se concentra la configuración principal de Django:

- `urls.py`
- `asgi.py`
- `wsgi.py`

Además, la configuración está separada en `config/settings/`, lo que permite diferenciar entornos y mantener orden técnico desde etapas tempranas:

- `base.py`
- `local.py`
- `production.py`

Esta separación es consistente con una arquitectura escalable y facilita futuras configuraciones para desarrollo, pruebas y despliegue.

### Apps base del sistema

Actualmente existen tres apps iniciales:

- `core`
- `operaciones`
- `usuarios`

Estas apps representan una primera separación funcional del sistema:

- `core`: componentes base o transversales
- `operaciones`: lógica relacionada al proceso operativo del MVP
- `usuarios`: elementos vinculados a usuarios, perfiles o gestión asociada

La definición exacta de responsabilidades podrá ajustarse en sprints posteriores, pero la separación inicial ya se encuentra establecida.

### Capa de dominio

Existe una carpeta `domain/` con la siguiente orientación:

- `entities/`
- `repositories/`
- `services/`

Esta capa busca desacoplar la lógica de negocio del framework y de las integraciones técnicas. Su objetivo es que las reglas del negocio del módulo puedan mantenerse organizadas y reutilizables.

### Capa de infraestructura

Existe una carpeta `infrastructure/` con integración inicial hacia `dataverse/`, incluyendo:

- `auth.py`
- `client.py`
- `mapping.py`
- `repositories/`

Esto deja registrada desde la base la intención de separar la integración externa del resto del sistema, evitando que el acceso a servicios o datos quede mezclado con la lógica del dominio o con las vistas del framework.

## Separación lógica inicial

La arquitectura actual ya refleja una separación lógica mínima entre capas:

### Configuración
Todo lo relativo al arranque y comportamiento global del proyecto se concentra en `config/` y `config/settings/`.

### Aplicación
Las apps Django (`core`, `operaciones`, `usuarios`) concentran la organización funcional inicial del sistema.

### Dominio
La carpeta `domain/` queda reservada para entidades, servicios y contratos de repositorio asociados a las reglas del negocio.

### Infraestructura
La carpeta `infrastructure/dataverse/` concentra autenticación, cliente técnico, mapeos y repositorios de integración.

Esta separación constituye una base válida para continuar en Sprint 2 con implementación sin partir desde una estructura improvisada.

## Criterios de organización documentados

La arquitectura base del módulo Python se regirá por los siguientes criterios iniciales:

1. **Separación entre configuración, negocio e integración**  
   La configuración del framework, la lógica del dominio y la infraestructura externa no deben quedar mezcladas.

2. **Crecimiento modular por componentes**  
   Las funcionalidades deberán incorporarse en módulos o apps con responsabilidades claras.

3. **Preparación para múltiples entornos**  
   La configuración debe mantenerse separada al menos entre entorno local y producción.

4. **Integraciones encapsuladas**  
   Todo acceso a Dataverse u otros servicios externos debe concentrarse en la capa de infraestructura.

5. **Documentación progresiva**  
   Este documento podrá ampliarse en siguientes sprints con decisiones técnicas, modelo de datos, convenciones y diagramas.

## Restricciones técnicas actuales

En la etapa actual se identifican las siguientes restricciones o condiciones:

- la arquitectura aún está en fase base y no representa una solución cerrada
- el modelo de datos definitivo todavía no está documentado en esta carpeta
- la integración con Dataverse está iniciada a nivel estructural, pero no se considera documentada funcionalmente en detalle
- existe una base local con `db.sqlite3`, útil para desarrollo inicial, pero no necesariamente representativa del entorno final
- la carpeta `.venv` corresponde al entorno local y no forma parte de la arquitectura funcional del producto

## Decisiones técnicas registradas hasta ahora

A la fecha quedan registradas las siguientes decisiones iniciales:

- uso de **Python + Django** como base del módulo web/backend
- uso de **settings separados por entorno**
- uso de **apps Django** para organización funcional inicial
- preparación de una **capa de dominio**
- preparación de una **capa de infraestructura** para integración con Dataverse

## Próximos registros de arquitectura

Este documento deberá ampliarse en siguientes iteraciones con:

- diagrama lógico del módulo Python
- definición de responsabilidades por app
- modelo de datos inicial
- estrategia de integración Python ↔ Dataverse
- flujo entre frontend, backend e integraciones
- decisiones técnicas relevantes del proyecto

## Relación con otros documentos

Este README de arquitectura complementa:

- la documentación general del repositorio raíz
- el README local de `python-app`
- los documentos de alcance, levantamiento y planificación del proyecto

## Conclusión

La arquitectura base del módulo Python ya se encuentra definida a nivel estructural mínimo.  
Existe una organización inicial de carpetas, módulos y separación lógica suficiente para considerar cerrada la etapa de definición base y continuar con la implementación del MVP en los siguientes sprints.