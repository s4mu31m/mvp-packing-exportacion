# Arquitectura del sistema alineada al modelo Dataverse (wiki 03.x)

> Referencia rectora: sección **03 - Modelo de datos y entidades** y sus subpáginas **03.2, 03.3 y 03.4** de la wiki del proyecto.
>
> Este archivo debe leerse como **documento técnico de apoyo para el backend y para agentes de desarrollo**, no como documento rector del modelo de datos. El **modelo rector** es el definido en Dataverse y documentado en la wiki 03.x.

---

## Objetivo

Documentar la arquitectura base del MVP dejando explícito que:

- **Dataverse es la estructura rectora del modelo de datos**;
- **Django/Python es la capa de lógica, validación, orquestación e integración**;
- los nombres de entidades, relaciones y códigos deben respetar la definición vigente en la wiki **03.x**;
- este documento no debe reinterpretar ni reemplazar la especificación del modelo Dataverse.

---

## Principio rector de modelado

Para cualquier avance futuro, agente, script, prueba o refactor, aplicar esta regla:

1. **La wiki 03.x manda sobre este archivo.**
2. **Dataverse manda sobre el modelo local Django cuando exista diferencia de naming o estructura.**
3. El modelo local en Django debe entenderse como **capa de implementación / espejo transicional**, no como fuente de verdad contractual.
4. Si aparece una discrepancia entre documentos históricos y la wiki 03.x, **se debe corregir el documento histórico**, no reinterpretar Dataverse.

---

## Responsabilidades por componente

| Componente | Rol real |
|---|---|
| **Dataverse** | Sistema rector del modelo estructural del MVP. Aquí viven las tablas, columnas, relaciones, claves de negocio, lookups y convenciones definitivas del proceso. |
| **Django / Python** | Capa de negocio e integración. Ejecuta validaciones, normalización, reglas operativas, construcción de payloads, consumo de Dataverse Web API y exposición de endpoints o UI. |
| **Wiki** | Fuente documental rectora del diseño funcional y técnico. La sección 03.x es la referencia principal para entidades y mapeo. |
| **Repositorio** | Materialización versionada del código, pruebas, documentos de apoyo y adaptadores técnicos. |

---

## Modelo rector que debe respetar el backend

A nivel documental y de naming, el backend debe alinearse con el modelo definido en 03.x, que distingue al menos estos planos:

- **entidades operacionales del proceso**;
- **relaciones entre entidades**;
- **códigos de negocio visibles al usuario**;
- **IDs técnicos o claves internas del sistema**;
- **mapeo entre implementación local y estructura Dataverse**.

### Criterio de nomenclatura obligatorio

Donde antes existía ambigüedad entre nombres genéricos del backend y la estructura objetivo, debe preferirse la nomenclatura del modelo Dataverse. En particular:

- usar **Bin** como entidad operativa de recepción;
- usar **LotePlanta** como entidad del proceso planta, evitando el uso ambiguo de **Lote** como nombre rector;
- usar **Pallet** como entidad de consolidación posterior al packing;
- respetar la existencia del dominio **Desverdizado** como parte del flujo documentado;
- tratar los códigos como **atributos de negocio** y no como sustitutos del identificador interno de Dataverse.

---

## Regla de alineación entre modelo local y modelo Dataverse

El proyecto puede seguir usando modelos locales en Django para facilitar:

- validación;
- pruebas unitarias;
- simulación local con SQLite;
- desarrollo desacoplado del ambiente del cliente.

Pero esos modelos deben mapear explícitamente a la estructura del modelo Dataverse documentado en 03.4.

### En términos prácticos

- **no** se debe seguir documentando el sistema como si `Bin`, `Lote`, `Pallet`, `BinLote`, `PalletLote` y `RegistroEtapa` fueran automáticamente la forma final del modelo rector;
- **sí** se puede mantener un modelo local equivalente o adaptador, siempre que quede claro que:
  - `Lote` local corresponde al concepto rector **LotePlanta**;
  - las tablas relacionales locales existen por necesidad de implementación, no necesariamente como contrato final de Dataverse;
  - la trazabilidad de etapas no debe deformar ni redefinir las entidades maestras del modelo.

---

## Vista general de arquitectura

```text
UI tablet-first / navegador
    ↓ HTTPS
Backend Python — Django
    ↓ OAuth2 client credentials
Microsoft Entra ID
    ↓ Access token
Dataverse
    ↓
Tablas rectoras del MVP:
Bin / LotePlanta / Desverdizado / Pallet / relaciones y lookups asociados
```

---

## Capas principales

### 1. Capa de presentación

- UI web responsive, tablet-first.
- Formularios rápidos para operación en planta.
- Vistas de consulta simples para jefatura.

### 2. Capa de aplicación

- Casos de uso.
- Orquestación del flujo.
- Validaciones previas a persistencia.
- Resolución de reglas de negocio.
- Armado de payloads para Dataverse.

### 3. Capa de dominio local

- DTOs, validadores, objetos de resultado y reglas reutilizables.
- Esta capa puede usar nombres internos equivalentes, pero debe documentar su correspondencia con 03.4.

### 4. Capa de infraestructura

- Cliente HTTP para Dataverse.
- Adquisición de token con Entra ID.
- Mapeadores entre objetos Python y tablas/columnas Dataverse.
- Manejo de errores, reintentos e idempotencia.

---

## Entidades rectoras a considerar en todo avance futuro

> Esta lista resume la línea documental vigente. Si la wiki 03.x profundiza o corrige alguno de estos puntos, prevalece la wiki.

| Entidad / concepto | Uso en el MVP |
|---|---|
| **Temporada** | Marco temporal y de correlatividad operacional. |
| **Bin** | Unidad operacional recibida desde etapas previas. |
| **LotePlanta** | Agrupación interna de planta generada desde recepción/pesaje. |
| **Desverdizado** | Subproceso formal del flujo cuando corresponde por condición operativa. |
| **Pallet** | Consolidación posterior a packing para continuidad logística. |
| **Planta / contexto operacional** | Referencia de ubicación, operación o contexto según modelo 03.x. |
| **Códigos de negocio** | Identificadores visibles como `id_bin`, `code_lote_planta`, `code_pallet` o equivalentes definidos en la wiki. |

---

## Implicancias para el backend

### 1. El backend no debe inventar el modelo

Los agentes o desarrolladores no deben:

- crear nombres de tablas por intuición;
- seguir usando términos históricos ambiguos;
- asumir que el modelo local Django define por sí solo el contrato final.

### 2. El backend sí debe adaptar su implementación

El backend sí debe:

- mantener mapeos claros entre nombres locales y nombres Dataverse;
- centralizar esos mapeos en una capa explícita;
- dejar trazabilidad de qué campo local corresponde a qué columna Dataverse;
- evitar que serializers, vistas o tests propaguen nomenclaturas obsoletas.

### 3. El backend debe soportar dos modos

- **modo local**: SQLite / entorno dev / simulación;
- **modo Dataverse**: persistencia real contra el modelo del cliente.

El cambio entre ambos no debe alterar el contrato funcional expuesto por los casos de uso.

---

## Ajuste explícito respecto del documento histórico anterior

El documento anterior hablaba de:

- `Lote` como entidad general;
- `BinLote` y `PalletLote` como si fueran necesariamente parte del diseño rector;
- `RegistroEtapa` como eje estructural del modelo.

Para alinearlo con la wiki 03.x, se debe entender ahora que:

- el concepto rector es **LotePlanta**;
- las relaciones técnicas del backend no deben sustituir el lenguaje del modelo funcional;
- la trazabilidad por etapa es una necesidad operativa, pero no debe desordenar la jerarquía de entidades maestras;
- la documentación del backend debe hablar en términos del modelo Dataverse y luego, si hace falta, explicar el espejo local.

---

## Recomendación de estructura interna para la integración

```text
python-app/
├── src/
│   ├── config/
│   ├── operaciones/
│   │   ├── application/
│   │   │   ├── use_cases/
│   │   │   ├── dto.py
│   │   │   ├── results.py
│   │   │   └── exceptions.py
│   │   ├── domain/
│   │   │   ├── entities/
│   │   │   ├── value_objects/
│   │   │   └── services/
│   │   ├── infrastructure/
│   │   │   └── dataverse/
│   │   │       ├── client.py
│   │   │       ├── auth.py
│   │   │       ├── mappers.py
│   │   │       ├── repositories.py
│   │   │       └── schemas.py
│   │   └── api/
│   └── tests/
```

### Nota importante

El archivo `mappers.py` o su equivalente debe ser tratado como punto crítico, porque ahí debe quedar la traducción entre:

- naming local de backend;
- nombres del modelo de dominio;
- columnas y lookups del Dataverse real.

---

## Estado esperado de la arquitectura

| Aspecto | Estado esperado |
|---|---|
| Separación de settings por entorno | Vigente |
| Modelo local de apoyo en Django | Permitido |
| Modelo rector Dataverse | Obligatorio |
| Mapeo explícito local ↔ Dataverse | Obligatorio |
| Casos de uso fuera de vistas | Obligatorio |
| Integración encapsulada en infraestructura | Obligatorio |
| Naming alineado a wiki 03.x | Obligatorio |

---

## Restricciones y advertencias

- SQLite sigue siendo solo un soporte de desarrollo local.
- No se debe presentar el modelo SQLite/Django como diseño final al cliente.
- Los nombres históricos del backend deben corregirse gradualmente para evitar deuda documental.
- Cualquier agente automático debe trabajar con este criterio:
  - **leer wiki 03.x como verdad del modelo**;
  - **usar estos documentos solo como guía de implementación alineada**.

---

## Instrucción operativa para agentes y colaboradores

Antes de proponer cambios en backend, tests, docs o integración:

1. revisar la wiki 03.x;
2. identificar la entidad Dataverse real involucrada;
3. verificar el nombre de negocio y el nombre técnico;
4. recién después proponer el cambio en Python;
5. si detecta conflicto documental, corregir primero la documentación de apoyo.

---

## Documentos relacionados

- `docs/arquitectura/reestructura-planificaion.md`
- `docs/arquitectura/preinicio-mvp.md`
- Wiki `03 - Modelo de datos y entidades`
- Wiki `03.2 - Especificación del modelo`
- Wiki `03.3 - Diagrama entidad-relación (ERD)`
- Wiki `03.4 - Mapeo a Dataverse`
