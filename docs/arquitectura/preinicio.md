# Preparación preinicio para MVP Python + Dataverse, alineado con wiki 03.x

> Este documento fue ajustado para que el preinicio técnico no contradiga la estructura del modelo definida en la wiki **03 - Modelo de datos y entidades** y sus subpáginas **03.2, 03.3 y 03.4**.
>
> Su función es dejar claros los prerrequisitos para construir sobre el modelo Dataverse ya definido, no rediseñarlo desde cero.

---

## Propósito del documento

Definir qué debe estar resuelto antes del kickoff técnico para que:

- el backend Python implemente correctamente el modelo rector;
- los accesos y el entorno Dataverse no bloqueen el desarrollo;
- la documentación que use un agente de trabajo sea consistente con la wiki 03.x;
- y el equipo no vuelva a caer en ambigüedades entre modelo local y modelo Dataverse.

---

## Regla base de preinicio

Antes de cualquier avance relevante, se debe asumir lo siguiente:

1. **La estructura del modelo está definida por la wiki 03.x.**
2. **Dataverse es el sistema rector de entidades, relaciones y columnas objetivo.**
3. **Django es la capa de lógica, integración y soporte local.**
4. Los documentos de preinicio, arquitectura y planificación deben limitarse a:
   - preparar accesos,
   - preparar integración,
   - preparar mapeos,
   - y reducir incertidumbre operativa.

---

## Resumen ejecutivo

El MVP corresponde a una primera etapa funcional del módulo de packing/exportación con backend Python y Dataverse como sistema rector de datos.

El preinicio debe dejar habilitado el trabajo sobre un flujo de trazabilidad mínima que, documentalmente, debe interpretarse con la estructura vigente de la wiki 03.x.

Eso implica que el equipo debe iniciar con claridad sobre:

- qué entidad es **Bin**;
- qué representa **LotePlanta** dentro del proceso;
- cómo participa **Desverdizado** en el flujo;
- cómo se consolida **Pallet**;
- y cómo se diferencia un **ID interno** de un **código operacional visible**.

---

## Objetivo práctico del preinicio

Llegar al kickoff con lo siguiente resuelto:

- ambiente Dataverse accesible;
- autenticación técnica disponible;
- definición clara del mapeo local ↔ Dataverse;
- naming documental consistente para backend y pruebas;
- reglas mínimas para modo local y modo Dataverse;
- y una base suficiente para que un agente continúe avances sin reinterpretar el modelo.

---

## Modelo que debe considerarse desde el día 1

Este documento ya no debe hablar del sistema como si el modelo rector fuera solamente el del backend local.

La preparación debe asumir como mínimo estos conceptos estructurales:

| Concepto | Lectura correcta |
|---|---|
| **Temporada** | Marco temporal del proceso y de correlatividad operacional. |
| **Bin** | Unidad operacional de entrada. |
| **LotePlanta** | Agrupación interna de planta; evitar usar “Lote” como nombre ambiguo cuando se habla del modelo rector. |
| **Desverdizado** | Parte formal del flujo cuando la condición del proceso lo requiere. |
| **Pallet** | Unidad de consolidación posterior al packing. |
| **Códigos de negocio** | Atributos visibles del modelo, por ejemplo `id_bin`, `code_lote_planta`, `code_pallet` o equivalentes definidos en la wiki. |
| **IDs internos / GUIDs / lookups** | Identificadores técnicos del sistema y de Dataverse. |

---

## Aclaración crítica sobre modelo local vs modelo rector

### Modelo local

El backend puede seguir usando:

- SQLite para desarrollo;
- modelos Django de apoyo;
- relaciones auxiliares para pruebas;
- servicios y casos de uso desacoplados.

### Modelo rector

Pero la preparación del proyecto debe dejar claro que:

- la verdad estructural está en Dataverse;
- el naming del backend debe converger hacia el naming documentado en 03.x;
- los adaptadores locales no deben presentarse como diseño contractual final.

---

## Condiciones críticas antes de iniciar

### Accesos y entorno

- URL del ambiente Dataverse confirmada.
- Acceso del desarrollador al ambiente.
- Permisos suficientes para revisar tablas, columnas, relaciones y soluciones.
- Validación de que el ambiente corresponde al modelo que se está documentando.

### Identidad y autenticación

- App registration en Entra ID.
- Client ID y secreto o certificado.
- Application User creado en Dataverse.
- Validación de acceso servidor a servidor con `WhoAmI`.

### Documentación y modelo

- Confirmación de que la wiki 03.x refleja la estructura vigente.
- Identificación del naming exacto de entidades y códigos.
- Confirmación del mapeo local ↔ Dataverse para backend.
- Registro de incompatibilidades documentales detectadas.

---

## Checklist mínimo de kickoff técnico

### Modelo y documentación

- [ ] Revisar 03 - Modelo de datos y entidades.
- [ ] Revisar 03.2 - Especificación del modelo.
- [ ] Revisar 03.3 - ERD.
- [ ] Revisar 03.4 - Mapeo a Dataverse.
- [ ] Confirmar que los documentos de apoyo no contradicen esos puntos.
- [ ] Corregir naming histórico que siga usando `Lote` como rector cuando corresponda `LotePlanta`.

### Entorno Dataverse

- [ ] Ambiente confirmado.
- [ ] Usuario con permisos.
- [ ] Tablas visibles.
- [ ] Columnas y relaciones verificadas.
- [ ] Solución base identificada.
- [ ] Validación de Web API operativa.

### Backend

- [ ] Variables de entorno definidas.
- [ ] Selector local / Dataverse definido.
- [ ] Cliente Dataverse listo para prueba.
- [ ] Mapeadores centralizados.
- [ ] Casos de uso preparados para persistencia intercambiable.

---

## Inventario mínimo que debe validarse antes de codificar

El preinicio debe dejar explícito cuáles son las piezas del modelo que el backend necesita conocer con certeza.

### A validar sí o sí

- entidad Dataverse de **Bin**;
- entidad Dataverse de **LotePlanta**;
- entidad o tabla relacionada con **Desverdizado**, si aplica al alcance inmediato;
- entidad Dataverse de **Pallet**;
- columnas técnicas e identificadores;
- columnas de códigos visibles de negocio;
- lookups y relaciones entre las entidades clave;
- reglas de obligatoriedad, unicidad y correlatividad.

---

## Estrategia recomendada de integración

### Principio

El backend no debe acoplarse a nombres “de memoria” ni a supuestos del modelo local. Debe usar una capa explícita de mapeo.

### Recomendación concreta

Centralizar en `infrastructure/dataverse/` o equivalente:

- autenticación;
- cliente HTTP;
- definición de nombres de tablas;
- definición de columnas;
- traducción entre DTOs internos y payloads Dataverse;
- resolución de lookups y claves alternativas si aplica.

---

## Modo local y modo Dataverse

Para no bloquear desarrollo, el proyecto puede seguir teniendo dos modos.

### Modo local

- SQLite;
- simulación del flujo;
- pruebas unitarias;
- desarrollo de casos de uso.

### Modo Dataverse

- persistencia real;
- consumo de Web API;
- validación del modelo rector;
- pruebas de integración reales.

### Regla

Ambos modos deben representar el mismo contrato funcional, aunque su forma interna no sea idéntica.

---

## Riesgos principales de preinicio

| Riesgo | Consecuencia | Mitigación |
|---|---|---|
| Documentación desalineada con 03.x | El agente avanza con un modelo equivocado | Corregir primero docs base de apoyo |
| Naming histórico en backend | DTOs, tests y payloads inconsistentes | Plan de convergencia de nombres |
| No separar ID técnico y código de negocio | Integración frágil y trazabilidad confusa | Documentar ambos desde el inicio |
| Accesos tardíos a Dataverse | Bloqueo del desarrollo real | Tratar accesos como condición de kickoff |
| Mapeo no centralizado | Duplicación y errores en integración | Un único módulo de mapeo Dataverse |

---

## Preguntas que deben quedar cerradas en preinicio

- ¿Cuál es el nombre exacto de cada entidad Dataverse involucrada?
- ¿Qué campos son IDs técnicos y cuáles son códigos operacionales?
- ¿Dónde vive formalmente el concepto de LotePlanta?
- ¿Cómo se representa Desverdizado en el modelo?
- ¿Qué relaciones o lookups conectan Bin, LotePlanta y Pallet?
- ¿Qué parte del modelo local Django es solo soporte y cuál ya refleja el contrato real?
- ¿Qué naming debe usarse en tests, API y documentación desde ahora?

---

## Instrucción explícita para agentes de desarrollo

Si un agente usa este archivo como referencia, debe actuar así:

1. leer primero la wiki 03.x;
2. tomar este archivo como checklist de preparación;
3. no redefinir entidades;
4. no inventar columnas ni relaciones;
5. documentar cualquier discrepancia detectada;
6. proponer cambios en backend ya alineados al modelo Dataverse.

---

## Estado esperado para declarar preinicio habilitado

El preinicio puede considerarse habilitado cuando:

- Dataverse está accesible;
- la autenticación técnica fue validada;
- el modelo 03.x fue revisado;
- el naming crítico quedó claro;
- existe estrategia local / Dataverse;
- la documentación base de apoyo ya no contradice la estructura rectora.

---

## Nota final

Este documento debe servir para reducir fricción al inicio del trabajo técnico.

No debe usarse para rediseñar el modelo del proyecto, sino para dejar preparado al equipo y a los agentes para **implementar correctamente el modelo ya definido en Dataverse y documentado en la wiki 03.x**.
